"""Adapter from The Things Network uplinks to SAMVA readings, independent of the broker."""

import logging
import math
import re
from datetime import datetime

from django.db import transaction
from rest_framework.exceptions import APIException

from sensors.constants import LORAWAN_PAYLOAD_FPORT, TTN_FORWARD_EVENT
from sensors.serializers import SensorIngestSerializer
from sensors.utils import resolve_sensor, store_reading

logger = logging.getLogger('sensors.mqtt')

# TTN stamps nanoseconds, more than `datetime` holds; the fraction is dropped anyway.
TTN_TIMESTAMP_PATTERN = re.compile(
    r'^(?P<seconds>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?(?P<offset>Z|[+-]\d{2}:\d{2})$'
)
PROBE_ID_MAX = 0xFFFF
VALUE_DECIMALS = 4


class LoRaPayloadError(Exception):
    """The uplink cannot be turned into readings; nothing from it is stored."""


def application_up(message):
    """Return the `ApplicationUp`, unwrapping the console/webhook event envelope."""
    if not isinstance(message, dict):
        raise LoRaPayloadError('The message is not a JSON object.')
    if message.get('name') == TTN_FORWARD_EVENT and isinstance(message.get('data'), dict):
        return message['data']
    return message


def device_identifiers(message):
    """`(dev_eui, device_id)` of the sender, `None` where the message does not say."""
    try:
        end_device_ids = application_up(message).get('end_device_ids') or {}
    except LoRaPayloadError:
        return None, None
    return end_device_ids.get('dev_eui'), end_device_ids.get('device_id')


def parse_received_at(raw_timestamp):
    # Truncated to the second so a QoS 1 redelivery carries the same instant as the
    # original and the unique (sensor_variable, recorded_at) constraint stores it once.
    match = TTN_TIMESTAMP_PATTERN.match(raw_timestamp) if isinstance(raw_timestamp, str) else None
    if match is None:
        raise LoRaPayloadError(f'Invalid uplink received_at: {raw_timestamp!r}.')
    offset = match['offset'].replace('Z', '+00:00')
    return datetime.fromisoformat(match['seconds'] + offset)


def parse_value(probe_id, semantic_key, value):
    if value is None:
        return None
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_number or not math.isfinite(value):
        raise LoRaPayloadError(
            f'Probe {probe_id} sent a non-numeric value for {semantic_key!r}: {value!r}.'
        )
    return round(value, VALUE_DECIMALS)


def parse_probe(probe, recorded_at):
    if not isinstance(probe, dict):
        raise LoRaPayloadError(f'Invalid probe entry: {probe!r}.')
    probe_id = probe.get('id')
    is_valid_id = isinstance(probe_id, int) and not isinstance(probe_id, bool)
    if not is_valid_id or not 0 <= probe_id <= PROBE_ID_MAX:
        raise LoRaPayloadError(f'Invalid probe id: {probe_id!r}.')
    readings = probe.get('readings')
    if not isinstance(readings, dict) or not readings:
        raise LoRaPayloadError(f'Probe {probe_id} has no readings.')

    return {
        'serial_number': str(probe_id),
        'recorded_at': recorded_at,
        'readings': [
            {'variable': semantic_key, 'value': parse_value(probe_id, semantic_key, value)}
            for semantic_key, value in readings.items()
        ],
    }


def parse_ttn_uplink(message):
    """Turn a TTN uplink into one ingest reading per probe.

    Accepts the `ApplicationUp` published on MQTT and the `as.up.data.forward` envelope
    the TTN console shows. The keys of each probe's `readings` are already `SemanticKey`
    values (the uplink formatter emits them), so no mapping table lives here.
    """
    uplink = application_up(message).get('uplink_message')
    if not isinstance(uplink, dict):
        raise LoRaPayloadError('The message carries no uplink_message.')

    f_port = uplink.get('f_port')
    if f_port != LORAWAN_PAYLOAD_FPORT:
        raise LoRaPayloadError(
            f'Unexpected fPort {f_port} (payload v2 travels on {LORAWAN_PAYLOAD_FPORT}).'
        )

    decode_errors = uplink.get('decode_errors')
    decoded_payload = uplink.get('decoded_payload')
    if decode_errors is None and isinstance(decoded_payload, dict):
        decode_errors = decoded_payload.get('errors')
    if decode_errors:
        raise LoRaPayloadError(f'The uplink formatter reported errors: {decode_errors}.')
    if not isinstance(decoded_payload, dict):
        raise LoRaPayloadError(
            'The uplink has no decoded_payload (is the TTN uplink formatter installed?).'
        )

    probes = decoded_payload.get('sensors')
    if not isinstance(probes, list) or not probes:
        raise LoRaPayloadError('The decoded_payload has no sensors.')

    recorded_at = parse_received_at(uplink.get('received_at'))
    return [parse_probe(probe, recorded_at) for probe in probes]


def store_probe(probe):
    sensor = resolve_sensor(probe['serial_number'])
    serializer = SensorIngestSerializer(data=probe)
    serializer.is_valid(raise_exception=True)
    return store_reading(sensor, serializer.validated_data)


def handle_uplink(message):
    """Store every probe of a TTN uplink and return `{'stored': n, 'rejected': m}`.

    Never raises: a node gets no answer, so each failure becomes one log line naming the
    device and probe, and the remaining probes (and the MQTT loop) carry on.
    """
    dev_eui, device_id = device_identifiers(message)
    outcome = {'stored': 0, 'rejected': 0}

    try:
        probes = parse_ttn_uplink(message)
    except LoRaPayloadError as error:
        log_rejection(dev_eui, device_id, None, error)
        outcome['rejected'] += 1
        return outcome

    for probe in probes:
        serial_number = probe['serial_number']
        try:
            # One savepoint per probe, so a database error in one leaves the connection
            # usable for the next.
            with transaction.atomic():
                created, duplicates = store_probe(probe)
        except APIException as error:
            log_rejection(dev_eui, device_id, serial_number, error.detail)
            outcome['rejected'] += 1
            continue
        except Exception:
            logger.exception(
                'LoRaWAN probe failed: dev_eui=%s device_id=%s serial=%s',
                dev_eui,
                device_id,
                serial_number,
            )
            outcome['rejected'] += 1
            continue

        outcome['stored'] += 1
        logger.info(
            'LoRaWAN probe stored: dev_eui=%s device_id=%s serial=%s created=%s duplicates=%s',
            dev_eui,
            device_id,
            serial_number,
            created,
            duplicates,
        )

    return outcome


def log_rejection(dev_eui, device_id, serial_number, reason):
    logger.warning(
        'LoRaWAN uplink rejected: dev_eui=%s device_id=%s serial=%s reason=%s',
        dev_eui,
        device_id,
        serial_number,
        reason,
    )
