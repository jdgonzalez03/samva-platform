import logging
from decimal import Decimal, InvalidOperation

from celery import shared_task

from sensors.models import WeatherMeasurement, WeatherSnapshot, WeatherStation

from sensors.weather_station_providers.weatherlink import fetch_weatherlink
from sensors.weather_station_providers.wunderground import fetch_wunderground
from sensors.weather_station_providers.other import fetch_other

logger = logging.getLogger(__name__)

PROVIDER_ADAPTERS = {
    'weatherlink': fetch_weatherlink,
    'wunderground': fetch_wunderground,
    'other': fetch_other,
}

def _safe_decimal(raw_value) -> Decimal | None:
    if raw_value is None or raw_value == '--':
        return None
    try:
        return Decimal(str(raw_value))
    except InvalidOperation:
        return None


@shared_task(max_retries=3)
def poll_weather_stations():
    logger.info('Polling weather stations.')
    stations = list(
        WeatherStation.objects.filter(is_active=True).prefetch_related(
            'station_variables__env_variable'
        )
    )

    if not stations:
        logger.info('There is not any data to ingest.')
        return

    for station in stations:
        logger.info('Polling data for station %s', station.name)
        try:
            adapter = PROVIDER_ADAPTERS.get(station.provider)
            if not adapter:
                logger.warning('Sin adaptador para proveedor "%s"', station.provider)
                continue

            result = adapter(station)
            raw_data = result['data']
            recorded_at = result['recorded_at']
            raw_response = result.get('raw')

            snapshot, created = WeatherSnapshot.objects.get_or_create(
                station=station,
                ingested_at=recorded_at.replace(second=0, microsecond=0),
                recorded_at=recorded_at, #TODO: Change this for 'generate_at' response in weatherlink data
                defaults={'raw_json': raw_response},
            )

            if not created:
                logger.info('WeatherSnapshot ya existe para %s @ %s', station, recorded_at)
                continue

            active_variables = station.station_variables.filter(is_active=True)
            data_records = []

            for station_variable in active_variables:
                raw_value = raw_data.get(station_variable.field_key)
                data_records.append(
                    WeatherMeasurement(
                        snapshot=snapshot,
                        station_variable=station_variable,
                        value=_safe_decimal(raw_value),
                    )
                )

            WeatherMeasurement.objects.bulk_create(data_records)
            logger.info(
                'Estación %s: %d variables ingestadas', station.name, len(data_records)
            )

        except Exception as error:
            logger.exception(
                'Error inesperado procesando estación %s, with error: %s',
                station.name, error,
            )
            raise
 