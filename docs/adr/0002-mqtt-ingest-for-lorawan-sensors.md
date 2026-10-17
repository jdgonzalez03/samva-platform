# ADR 0002: Ingest LoRaWAN sensor readings over MQTT from The Things Network

- **Status**: Accepted
- **Date**: 2026-09-30 (proposed), 2026-10-05 (accepted)
- **Scope**: `backend/sensors/`, `backend/docker-compose.yml`, the node firmware and TTN uplink formatter in `docs/test-sensors/`

## Context

Field sensors reach the platform today through one door: `POST /api/sensors/ingest/`, authenticated with the farmer's `X-API-Key`, one timestamped reading per request, idempotent on resend (see [sensor-ingest-api.md](../sensor-ingest-api.md)). It was designed for a device that can make an HTTPS request itself, such as an ESP32 on Wi-Fi.

The real hardware is different. The nodes are **LoRaWAN** devices (today a Raspberry Pi Pico 2W with an LA66 module standing in for the PCB). They radio to a **Dragino gateway**, which forwards the encrypted packets to **The Things Network (TTN, cluster `au1`)**. TTN decrypts them, runs our uplink formatter ([response-format.js](../test-sensors/response-format.js)) and publishes the result. The first draft of this ADR assumed the gateway published MQTT itself; a captured message ([response.json](../test-sensors/response.json)) showed that **TTN, not the gateway, is the publisher**.

Two more constraints shape the decision:

- The platform will be deployed on a **Raspberry Pi 5 (8 GB RAM, SD card)**, possibly behind NAT or a 4G router, without a public IP.
- A LoRaWAN node cannot be answered per message. Whatever goes wrong with a reading (unknown probe, unexpected field) has to be visible to us, because the device will never see an error.

## Decision

Add MQTT as a **second ingest channel** next to the HTTP endpoint, both writing through the same storage logic, and **subscribe directly to TTN's MQTT broker**.

```
Pico/PCB ──radio──▶ Dragino gateway ──▶ TTN (decrypt + response-format.js)
                                          │ MQTT over TLS :8883  v3/<app>@ttn/devices/+/up
                                          ▼
simulate_lora_node.py ──▶ Mosquitto (dev only, :1883)
                                          │
                                          ▼
                       mqtt_ingest (Django command, compose service)
                                          │ sensors/lorawan.py: ApplicationUp → one reading per probe
                                          ▼
                       store_reading()  ◀── also behind POST /api/sensors/ingest/
                                          ▼
                                       PostGIS
```

1. **TTN is the broker in every real environment.** The connection is outbound from our side (TLS on 8883), so it works from a laptop, from the Pi behind NAT and in production alike. Credentials are the application id (`<app>@ttn` as username) and a TTN API key with *Read application traffic* as password; they are the trust boundary of this channel.
2. **Mosquitto stays as a development broker only.** It is the target of `backend/scripts/simulate_lora_node.py`, which publishes TTN-shaped uplinks so the whole pipeline can be exercised at home without hardware. One switch, `MQTT_SOURCE=local|ttn` (default `local`), picks the profile in `settings.MQTT_INGEST`.
3. **Payload v2: one block per physical probe.** Each probe travels as `[id u16][values…]`, big-endian, 46 bytes in total, on **fPort 3** (the port versions the layout; a v1 payload on fPort 2 is rejected rather than misdecoded). The formatter emits `{"sensors": [{"id": 101, "readings": {"air_temperature": 22.98, …}}, …]}` whose keys are `SemanticKey` values, so the backend needs no mapping table.
4. **One `FieldSensor` per probe, resolved by its id alone.** The probe id is the sensor's `serial_number` (globally unique). `ingest_reading` is split into `resolve_sensor(serial, farmer=None)` and `store_reading(sensor, reading)`: HTTP keeps scoping the lookup to the API key's farmer, MQTT looks the serial up globally. The owner follows from sensor → plot → farm. The farmer's API secret does **not** travel in the payload: it does not fit at SF10–12, would be exposed over the air, and would force a reflash every time it is regenerated.
5. **`recorded_at` is TTN's `uplink_message.received_at`, truncated to the second.** A redelivery carries the same value, so `SensorMeasurement`'s unique `(sensor_variable, recorded_at)` stores it once.
6. **Rejected messages are logged, never raised.** An unknown serial, an inactive sensor, an unmapped variable or a payload the formatter could not decode produces one structured line on the `sensors.mqtt` logger (`dev_eui`, `device_id`, `serial`, reason) and the subscriber moves on to the next probe. `make mqtt-logs` shows them.
7. **The subscriber is resilient, not durable.** `mqtt_ingest` subscribes with QoS 1, reconnects with backoff and runs with `restart: unless-stopped`. TTN's broker does **not** queue messages for a disconnected subscriber, so uplinks that arrive while `mqtt_ingest` is down are lost.
8. **The HTTP endpoint stays.** It still serves devices that can speak HTTPS, the integration tests and manual backfills.

## Alternatives considered

- **Own Mosquitto fed by the gateway.** The gateway hands *encrypted* frames to TTN's network server; getting plaintext into Mosquitto means leaving TTN for our own LoRaWAN network server (ChirpStack) or running a TTN→Mosquitto bridge that subscribes to TTN anyway. High effort for no gain at this stage.
- **TTN webhook (HTTP POST to the backend).** Reuses the HTTP stack, but needs a public HTTPS URL: ngrok in development and a public IP or domain in production, which the Pi deployment does not have.
- **RabbitMQ's MQTT plugin instead of Mosquitto (dev).** Couples device traffic to the Celery broker and needs a custom image.
- **Consuming MQTT from a Celery worker.** Celery consumes AMQP task messages, not arbitrary MQTT topics; it would need the same custom subscriber anyway.

## Consequences

- One new dependency (`paho-mqtt`, pinned in `backend/requirements.txt`) and one new service (`mqtt_ingest`); Mosquitto stays dev-only.
- Readings depend on the internet link and on TTN being up; while either is down, or while `mqtt_ingest` is stopped, uplinks are lost. TTN's *Storage Integration* can backfill gaps in a later phase.
- Devices get no feedback, so `last_seen_at`, the "Sin reportar" status in the dashboard and the `sensors.mqtt` logs are the only way to notice a misconfigured node.
- Registering a node means registering **each probe**: a `FieldSensor` whose serial number is the probe id compiled into the firmware, with the variables that probe sends.
- Simulated and real data share one database; keep them apart by serial (the simulator's 101–109 live on the demo plot loaded by `make loaddata`).

## Resolved questions

1. **Topic and shape**: `v3/<app>@ttn/devices/<device_id>/up`, one `ApplicationUp` per uplink carrying every probe of the node.
2. **Device identifier and timestamp**: `end_device_ids.dev_eui`/`device_id` identify the node (logged only); each probe carries its own id; `uplink_message.received_at` is the timestamp.
3. **Variables**: `SemanticKey` gained `leaf_temperature`, `soil_temperature`, `soil_water_tension`, `co2`, `battery_voltage`, `battery_current`, `solar_panel_voltage` and `solar_panel_current`; the auxiliary humidity is no longer sent.
4. **Units**: the formatter converts the raw integers to engineering units (°C, %, kPa, ppm, V, mA) before they reach us.

## How to simulate the node

```bash
cd backend
docker compose up -d backend mqtt mqtt_ingest
make loaddata                                  # registers the demo probes 101–109
make simulate-lora ARGS="--count 3 --interval 5"
make mqtt-logs                                 # 9 "probe stored" lines per uplink
```

Without `--count` the simulator publishes every 60 s until stopped. Automated tests cover the adapter, the handler and the command with a fake paho client, without a broker.
