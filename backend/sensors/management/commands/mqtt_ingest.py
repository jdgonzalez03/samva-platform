import json
import logging

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from sensors.constants import (
    MQTT_KEEPALIVE_SECONDS,
    MQTT_RECONNECT_MAX_DELAY_SECONDS,
    MQTT_RECONNECT_MIN_DELAY_SECONDS,
    MQTT_SOURCES,
)
from sensors.lorawan import handle_uplink

logger = logging.getLogger('sensors.mqtt')

SUBSCRIBE_QOS = 1


class Command(BaseCommand):
    help = (
        'Subscribe to the LoRaWAN uplinks (The Things Network or the local Mosquitto, per '
        'MQTT_SOURCE) and store every probe reading. Runs until stopped.'
    )

    def handle(self, *args, **options):
        config = self.validated_config()
        self.configure_logging()

        client = self.build_client(config)
        self.stdout.write(
            f'mqtt_ingest: source={config["source"]} broker={config["host"]}:{config["port"]} '
            f'tls={config["tls"]} topic={config["topic"]}'
        )
        client.connect_async(config['host'], config['port'], keepalive=MQTT_KEEPALIVE_SECONDS)
        # Reconnects on its own, with the backoff set in `build_client`, for as long as the
        # process lives; `on_connect` subscribes again after every reconnection.
        client.loop_forever(retry_first_connection=True)

    def validated_config(self):
        if settings.MQTT_SOURCE not in MQTT_SOURCES:
            raise CommandError(
                f'MQTT_SOURCE must be one of {", ".join(MQTT_SOURCES)}, '
                f'not {settings.MQTT_SOURCE!r}.'
            )
        config = settings.MQTT_INGEST
        if config['source'] == 'ttn' and not (config['app_id'] and config['password']):
            raise CommandError('MQTT_SOURCE=ttn needs TTN_APP_ID and TTN_API_KEY.')
        return config

    def configure_logging(self):
        # Django only configures its own loggers; without a handler the per-probe INFO lines
        # of this long-running process would never reach `docker compose logs`.
        if logger.handlers:
            return
        handler = logging.StreamHandler(self.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    def build_client(self, config):
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=config['client_id'],
            # A persistent session lets a broker that keeps sessions (Mosquitto) queue the
            # QoS 1 uplinks published while this subscriber restarts.
            clean_session=False,
        )
        if config['username']:
            client.username_pw_set(config['username'], config['password'])
        if config['tls']:
            client.tls_set()
        client.reconnect_delay_set(
            min_delay=MQTT_RECONNECT_MIN_DELAY_SECONDS,
            max_delay=MQTT_RECONNECT_MAX_DELAY_SECONDS,
        )
        client.user_data_set(config)
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        return client


def on_connect(client, config, flags, reason_code, properties):
    if reason_code.is_failure:
        logger.error(
            'MQTT connection refused: source=%s broker=%s:%s reason=%s',
            config['source'],
            config['host'],
            config['port'],
            reason_code,
        )
        return
    logger.info(
        'MQTT connected: source=%s broker=%s:%s topic=%s',
        config['source'],
        config['host'],
        config['port'],
        config['topic'],
    )
    client.subscribe(config['topic'], qos=SUBSCRIBE_QOS)


def on_disconnect(client, config, disconnect_flags, reason_code, properties):
    logger.warning(
        'MQTT disconnected: source=%s reason=%s (reconnecting)', config['source'], reason_code
    )


def on_message(client, config, message):
    try:
        payload = json.loads(message.payload)
    except (ValueError, UnicodeDecodeError) as error:
        logger.warning('MQTT message is not JSON: topic=%s error=%s', message.topic, error)
        return

    try:
        # The process outlives any single database connection (a Postgres restart, an idle
        # timeout), so stale ones are dropped before each message touches the ORM.
        close_old_connections()
        handle_uplink(payload)
    except Exception:
        # paho re-raises callback errors out of `loop_forever`, which would end the
        # subscriber over a single message.
        logger.exception('MQTT message could not be handled: topic=%s', message.topic)
