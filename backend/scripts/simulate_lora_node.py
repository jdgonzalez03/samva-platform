"""Simulate the LoRaWAN node as The Things Network would deliver it, for development.

Values follow a daily curve (a reduced `NodoSimulado` from docs/test-sensors/code-python.py),
are packed with the firmware's exact `struct` layout, decoded by a Python port of
docs/test-sensors/response-format.js, and published as a TTN `ApplicationUp` to the local
Mosquitto, where `mqtt_ingest` (MQTT_SOURCE=local) picks them up.

    make simulate-lora ARGS="--count 3 --interval 5"
"""

import argparse
import base64
import json
import math
import random
import struct
import sys
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

APP_ID = 'agriculture-unillanos'
DEVICE_ID = 'nodo-sim-0'
DEV_EUI = '0000000000000000'
FPORT = 3
LOCAL_TIMEZONE = ZoneInfo('America/Bogota')

# Same IDs and layout as the firmware (code-python.py): [id u16][values…] per probe.
ID_AIRE = 101
ID_FOLIAR = 102
ID_AUX = 103
ID_CO2 = 104
ID_WM1 = 105
ID_WM2 = 106
ID_WM3 = 107
ID_SUELO = 108
ID_ENERGIA = 109
FORMATO = '>HhHHhhHhHHHHHHHHHhHHhHH'
PAYLOAD_LENGTH = struct.calcsize(FORMATO)


def node_values(moment, noise):
    """One reading of every probe at `moment`, on the daily curves of the Llanos."""
    hour = moment.astimezone(LOCAL_TIMEZONE)
    hour = hour.hour + hour.minute / 60
    sunlight = max(0.0, math.sin(math.pi * (hour - 6) / 12))
    cycle = math.cos(2 * math.pi * (hour - 15) / 24)

    air_temperature = 26.5 + 5.0 * cycle + 1.2 * sunlight + noise.gauss(0, 0.1)
    # The Watermarks dry over a three-day irrigation cycle.
    drying = (moment.timestamp() % (3 * 86400)) / (3 * 86400)
    panel_current = 750 * sunlight + noise.gauss(0, 10) if sunlight > 0.03 else 0.0
    return {
        't_aire': air_temperature,
        'h_aire': min(99.5, max(35, 78 - 18 * cycle - 6 * sunlight + noise.gauss(0, 0.4))),
        't_hoja': air_temperature + sunlight * -1.5 - (1 - sunlight) * 0.8,
        't_amb_ir': air_temperature + 0.6 * sunlight,
        't_aux': air_temperature - 1.2,
        'co2': 430 + 110 * (1 - sunlight) + noise.gauss(0, 8),
        'wm1': 10 + 50 * drying + noise.gauss(0, 0.15),
        'wm2': 10 + 35 * drying + noise.gauss(0, 0.15),
        'wm3': 10 + 22 * drying + noise.gauss(0, 0.15),
        't_suelo': 25.5 + 2.0 * math.cos(2 * math.pi * (hour - 17) / 24),
        'v_bat': 3.85 + 0.25 * sunlight + noise.gauss(0, 0.005),
        'i_bat': panel_current * 0.6 - 45,
        'v_pan': 5.8 + 0.8 * sunlight if sunlight > 0.03 else 0.2,
        'i_pan': max(0.0, panel_current),
    }


def encode(values):
    """Byte-for-byte the firmware's `codificar`."""
    return struct.pack(
        FORMATO,
        ID_AIRE,
        round(values['t_aire'] * 100),
        round(values['h_aire'] * 100),
        ID_FOLIAR,
        round(values['t_hoja'] * 100),
        round(values['t_amb_ir'] * 100),
        ID_AUX,
        round(values['t_aux'] * 100),
        ID_CO2,
        round(values['co2']),
        ID_WM1,
        round(values['wm1'] * 10),
        ID_WM2,
        round(values['wm2'] * 10),
        ID_WM3,
        round(values['wm3'] * 10),
        ID_SUELO,
        round(values['t_suelo'] * 100),
        ID_ENERGIA,
        round(values['v_bat'] * 1000),
        round(values['i_bat']),
        round(values['v_pan'] * 1000),
        round(values['i_pan']),
    )


def decode(payload, f_port):
    """Python port of response-format.js: what TTN puts in `decoded_payload`."""
    if f_port != FPORT or len(payload) < PAYLOAD_LENGTH:
        return {'errors': [f'Payload inesperado (fPort {f_port}, {len(payload)} bytes)']}

    (
        aire_id, t_aire, h_aire,
        foliar_id, t_hoja, t_amb_ir,
        aux_id, t_aux,
        co2_id, co2,
        wm1_id, wm1, wm2_id, wm2, wm3_id, wm3,
        suelo_id, t_suelo,
        energia_id, v_bat, i_bat, v_pan, i_pan,
    ) = struct.unpack(FORMATO, payload[:PAYLOAD_LENGTH])  # fmt: skip

    sensors = [
        {'id': aire_id, 'readings': {
            'air_temperature': t_aire / 100, 'relative_humidity': h_aire / 100}},
        {'id': foliar_id, 'readings': {
            'leaf_temperature': t_hoja / 100, 'air_temperature': t_amb_ir / 100}},
        {'id': aux_id, 'readings': {'air_temperature': t_aux / 100}},
        {'id': co2_id, 'readings': {'co2': co2}},
        {'id': wm1_id, 'readings': {'soil_water_tension': wm1 / 10}},
        {'id': wm2_id, 'readings': {'soil_water_tension': wm2 / 10}},
        {'id': wm3_id, 'readings': {'soil_water_tension': wm3 / 10}},
        {'id': suelo_id, 'readings': {'soil_temperature': t_suelo / 100}},
        {'id': energia_id, 'readings': {
            'battery_voltage': v_bat / 1000,
            'battery_current': i_bat,
            'solar_panel_voltage': v_pan / 1000,
            'solar_panel_current': i_pan,
        }},
    ]  # fmt: skip
    return {
        'sensors': sensors,
        'delta_t_hoja_aire': round((t_hoja - t_aire) / 100, 2),
    }


def application_up(payload, f_cnt, received_at, device_id=DEVICE_ID, app_id=APP_ID):
    """The JSON TTN publishes on `v3/<app>@ttn/devices/<device>/up`, trimmed to what we read."""
    timestamp = received_at.astimezone(UTC).isoformat(timespec='microseconds')
    end_device_ids = {
        'device_id': device_id,
        'application_ids': {'application_id': app_id},
        'dev_eui': DEV_EUI,
    }
    return {
        'end_device_ids': end_device_ids,
        'received_at': timestamp.replace('+00:00', 'Z'),
        'uplink_message': {
            'f_port': FPORT,
            'f_cnt': f_cnt,
            'frm_payload': base64.b64encode(payload).decode(),
            'decoded_payload': decode(payload, FPORT),
            'received_at': timestamp.replace('+00:00', 'Z'),
        },
    }


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--interval', type=float, default=60, help='Seconds between uplinks.')
    parser.add_argument('--count', type=int, default=0, help='Uplinks to send (0 = forever).')
    parser.add_argument('--host', default='mqtt', help='MQTT broker host.')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port.')
    parser.add_argument('--device-id', default=DEVICE_ID, help='TTN device id in the topic.')
    parser.add_argument('--app-id', default=APP_ID, help='TTN application id in the topic.')
    parser.add_argument('--seed', type=int, help='Make the generated values reproducible.')
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    noise = random.Random(arguments.seed)
    topic = f'v3/{arguments.app_id}@ttn/devices/{arguments.device_id}/up'

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect(arguments.host, arguments.port)
    client.loop_start()

    f_cnt = 0
    try:
        while arguments.count == 0 or f_cnt < arguments.count:
            f_cnt += 1
            now = datetime.now(UTC)
            payload = encode(node_values(now, noise))
            message = application_up(payload, f_cnt, now, arguments.device_id, arguments.app_id)
            client.publish(topic, json.dumps(message), qos=1).wait_for_publish()
            print(f'[{now:%H:%M:%S}] f_cnt={f_cnt} {len(payload)} bytes -> {topic}', flush=True)
            if arguments.count == 0 or f_cnt < arguments.count:
                time.sleep(arguments.interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == '__main__':
    sys.exit(main())
