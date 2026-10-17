from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from predictions.constants import IRRIGATION_INPUT_KEYS
from predictions.fuzzy import predict_irrigation
from predictions.models import IrrigationPrediction, PredictionStatus
from sensors.aggregation import history_measurements
from sensors.models import WeatherMeasurement


class MissingSensorData(Exception):
    def __init__(self, missing):
        super().__init__(f'No recent readings for: {", ".join(missing)}')
        self.missing = missing


def field_sensor_averages(plot, filters):
    rows = (
        history_measurements(plot.farm, plot, filters)
        .filter(
            sensor_variable__use_in_predictions=True,
            sensor_variable__env_variable__semantic_key__in=IRRIGATION_INPUT_KEYS.values(),
        )
        .values('sensor_variable__env_variable__semantic_key')
        .annotate(average=Avg('value'))
        .order_by()
    )
    return {
        row['sensor_variable__env_variable__semantic_key']: float(row['average']) for row in rows
    }


def weather_station_averages(plot, filters):
    # A station covers the whole farm, so every plot of the farm shares its readings.
    rows = (
        WeatherMeasurement.objects.filter(
            station_variable__station__farm_id=plot.farm_id,
            station_variable__station__is_active=True,
            station_variable__is_active=True,
            station_variable__use_in_predictions=True,
            station_variable__env_variable__semantic_key__in=IRRIGATION_INPUT_KEYS.values(),
            value__isnull=False,
            snapshot__recorded_at__gte=filters['date_from'],
            snapshot__recorded_at__lt=filters['date_to'],
        )
        .values('station_variable__env_variable__semantic_key')
        .annotate(average=Avg('value'))
        .order_by()
    )
    return {
        row['station_variable__env_variable__semantic_key']: float(row['average'])
        for row in rows
    }


def recent_input_averages(plot, hours):
    """Average of each irrigation input over the last `hours`, and where it came from.

    Returns `(averages, input_sources)`: `averages` is keyed by model input, and
    `input_sources` gives each input's `field` and `station` averages (None when that source
    had no readings). Each available source weighs the same, so a station polled every
    5 minutes does not outvote a node reporting every minute just by sampling more often.
    """
    now = timezone.now()
    filters = {'date_from': now - timedelta(hours=hours), 'date_to': now}
    field_averages = field_sensor_averages(plot, filters)
    station_averages = weather_station_averages(plot, filters)

    averages = {}
    input_sources = {}
    missing = []
    for model_input, semantic_key in IRRIGATION_INPUT_KEYS.items():
        sources = {
            'field': field_averages.get(semantic_key),
            'station': station_averages.get(semantic_key),
        }
        available = [average for average in sources.values() if average is not None]
        if not available:
            missing.append(semantic_key)
            continue
        averages[model_input] = sum(available) / len(available)
        input_sources[model_input] = {
            source: None if average is None else round(average, 2)
            for source, average in sources.items()
        }

    if missing:
        raise MissingSensorData(missing)

    return averages, input_sources


def create_irrigation_prediction(plot, hours):
    averages, input_sources = recent_input_averages(plot, hours)
    result = predict_irrigation(**averages)
    return IrrigationPrediction.objects.create(
        plot=plot,
        avg_moisture=round(averages['moisture'], 2),
        avg_temperature=round(averages['temperature'], 2),
        avg_radiation=round(averages['radiation'], 2),
        avg_period_hours=hours,
        irrigation_time_minutes=result.minutes,
        output_label=result.label,
        input_memberships=result.input_memberships,
        output_activation=result.output_activation,
        clipped_inputs=result.clipped_inputs,
        input_sources=input_sources,
        status=PredictionStatus.COMPLETED,
        completed_at=timezone.now(),
    )
