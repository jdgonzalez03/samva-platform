from collections import defaultdict

from django.db import models
from django.db.models import Avg, F, Value
from django.utils import timezone

from farm.constants import (
    CHANGE_LOOKBACK,
    CHANGE_TOLERANCE,
    CONDITION_ORDER,
    OVERVIEW_BUCKET,
    OVERVIEW_SERIES_SPAN,
)
from farm.models import Plot
from predictions.constants import IRRIGATION_INPUT_KEYS
from predictions.fuzzy import input_term_degrees
from predictions.models import IrrigationPrediction
from sensors.aggregation import DateBin, build_series, history_measurements
from sensors.models import FieldSensor, SemanticKey, SensorMeasurement

MODEL_INPUT_BY_KEY = {key: model_input for model_input, key in IRRIGATION_INPUT_KEYS.items()}

PLOT_ID = 'sensor_variable__sensor__plot_id'
SEMANTIC_KEY = 'sensor_variable__env_variable__semantic_key'


def _active_measurements(**scope):
    return SensorMeasurement.objects.filter(
        sensor_variable__sensor__is_active=True,
        value__isnull=False,
        **scope,
    ).exclude(**{SEMANTIC_KEY: SemanticKey.OTHER})


def _latest_per_plot_and_key(measurements):
    # PostgreSQL `DISTINCT ON`: one row per (plot, variable) in a single query.
    return (
        measurements.select_related('sensor_variable__env_variable', 'sensor_variable__sensor')
        .order_by(PLOT_ID, SEMANTIC_KEY, '-recorded_at', '-id')
        .distinct(PLOT_ID, SEMANTIC_KEY)
    )


def _condition_sort_key(condition):
    key = condition['semantic_key']
    return CONDITION_ORDER.index(key) if key in CONDITION_ORDER else len(CONDITION_ORDER)


def _level(semantic_key, value):
    model_input = MODEL_INPUT_BY_KEY.get(semantic_key)
    if model_input is None:
        return None, None
    degrees = input_term_degrees(model_input, value)
    return max(degrees, key=degrees.get), degrees


def _conditions_by_plot(measurements, now):
    """Latest reading of every variable of every plot, with its change over 24 h."""
    change_cutoff = now - CHANGE_LOOKBACK
    previous_values = {
        (measurement.sensor_variable.sensor.plot_id, measurement.sensor_variable.env_variable.semantic_key): float(
            measurement.value
        )
        for measurement in _latest_per_plot_and_key(
            measurements.filter(
                recorded_at__lte=change_cutoff,
                recorded_at__gt=change_cutoff - CHANGE_TOLERANCE,
            )
        )
    }

    conditions = defaultdict(list)
    for measurement in _latest_per_plot_and_key(measurements):
        variable = measurement.sensor_variable.env_variable
        plot_id = measurement.sensor_variable.sensor.plot_id
        value = float(measurement.value)
        previous = previous_values.get((plot_id, variable.semantic_key))
        level, degrees = _level(variable.semantic_key, value)
        conditions[plot_id].append(
            {
                'semantic_key': variable.semantic_key,
                'name': variable.name,
                'unit': variable.unit,
                'value': value,
                'recorded_at': measurement.recorded_at,
                'change_24h': None if previous is None else round(value - previous, 2),
                'level': level,
                'level_degrees': degrees,
            }
        )
    return {
        plot_id: sorted(plot_conditions, key=_condition_sort_key)
        for plot_id, plot_conditions in conditions.items()
    }


def _farm_conditions(conditions_by_plot):
    """Each variable averaged over the plots that measure it."""
    by_key = defaultdict(list)
    for plot_conditions in conditions_by_plot.values():
        for condition in plot_conditions:
            by_key[condition['semantic_key']].append(condition)

    farm_conditions = []
    for key, rows in by_key.items():
        value = sum(row['value'] for row in rows) / len(rows)
        changes = [row['change_24h'] for row in rows if row['change_24h'] is not None]
        level, degrees = _level(key, value)
        farm_conditions.append(
            {
                'semantic_key': key,
                'name': rows[0]['name'],
                'unit': rows[0]['unit'],
                'value': round(value, 2),
                'recorded_at': max(row['recorded_at'] for row in rows),
                'change_24h': round(sum(changes) / len(changes), 2) if changes else None,
                'level': level,
                'level_degrees': degrees,
            }
        )
    return sorted(farm_conditions, key=_condition_sort_key)


def _series_start(now):
    # Hour-aligned origin so every bucket is a clock hour, which the heatmaps need.
    return (now - OVERVIEW_SERIES_SPAN).replace(minute=0, second=0, microsecond=0)


def _series_by_plot(farm, series_start, now):
    """Hourly average of every variable of every plot, as `{plot_id: {key: points}}`."""
    rows = (
        history_measurements(farm, None, {'date_from': series_start, 'date_to': now})
        .exclude(**{SEMANTIC_KEY: SemanticKey.OTHER})
        .annotate(
            bucket=DateBin(
                Value(OVERVIEW_BUCKET, output_field=models.DurationField()),
                F('recorded_at'),
                Value(series_start),
            )
        )
        .values(PLOT_ID, SEMANTIC_KEY, 'bucket')
        .annotate(average=Avg('value'))
        .order_by(PLOT_ID, SEMANTIC_KEY, 'bucket')
    )
    series = defaultdict(lambda: defaultdict(list))
    for row in rows:
        series[row[PLOT_ID]][row[SEMANTIC_KEY]].append(
            {'t': row['bucket'], 'value': round(float(row['average']), 2)}
        )
    return series


def build_conditions(plot, now):
    return _conditions_by_plot(_active_measurements(sensor_variable__sensor__plot=plot), now).get(
        plot.pk, []
    )


def build_plot_overview(plot):
    now = timezone.now()
    series_start = _series_start(now)
    series_measurements = history_measurements(
        plot.farm, plot, {'date_from': series_start, 'date_to': now}
    ).exclude(**{SEMANTIC_KEY: SemanticKey.OTHER})

    return {
        'generated_at': now,
        'conditions': build_conditions(plot, now),
        'series': build_series(series_measurements, series_start, OVERVIEW_BUCKET),
        'sensors': FieldSensor.objects.filter(plot=plot)
        .select_related('plot')
        .prefetch_related('sensor_variables__env_variable')
        .order_by('name', 'id'),
        'irrigation': plot.irrigation_predictions.order_by('-requested_at', '-id').first(),
    }


def build_farm_overview(farm):
    now = timezone.now()
    series_start = _series_start(now)
    conditions_by_plot = _conditions_by_plot(
        _active_measurements(sensor_variable__sensor__plot__farm=farm), now
    )
    series_by_plot = _series_by_plot(farm, series_start, now)
    latest_irrigation = _latest_irrigation_by_plot(plot__farm=farm)
    farm_series_measurements = history_measurements(
        farm, None, {'date_from': series_start, 'date_to': now}
    ).exclude(**{SEMANTIC_KEY: SemanticKey.OTHER})

    plots = []
    for plot in farm.plots.order_by('name', 'id'):
        plot_conditions = conditions_by_plot.get(plot.pk, [])
        plots.append(
            {
                'id': plot.pk,
                'name': plot.name,
                'latest_reading_at': max(
                    (condition['recorded_at'] for condition in plot_conditions), default=None
                ),
                'conditions': plot_conditions,
                'series': [
                    {'semantic_key': key, 'points': points}
                    for key, points in series_by_plot.get(plot.pk, {}).items()
                ],
                'irrigation': latest_irrigation.get(plot.pk),
            }
        )

    return {
        'generated_at': now,
        'conditions': _farm_conditions(conditions_by_plot),
        'series': build_series(farm_series_measurements, series_start, OVERVIEW_BUCKET),
        'plots': plots,
        'sensors': FieldSensor.objects.filter(plot__farm=farm)
        .select_related('plot')
        .prefetch_related('sensor_variables__env_variable')
        .order_by('plot__name', 'name', 'id'),
    }


def _latest_irrigation_by_plot(**scope):
    return {
        prediction.plot_id: prediction
        for prediction in IrrigationPrediction.objects.filter(**scope)
        .order_by('plot_id', '-requested_at', '-id')
        .distinct('plot_id')
    }


def build_plot_summaries(user):
    """Every plot the user owns, across farms, with its latest readings."""
    now = timezone.now()
    conditions_by_plot = _conditions_by_plot(
        _active_measurements(sensor_variable__sensor__plot__farm__owner__user=user), now
    )
    latest_irrigation = _latest_irrigation_by_plot(plot__farm__owner__user=user)

    summaries = []
    for plot in (
        Plot.objects.filter(farm__owner__user=user)
        .with_sensor_count()
        .select_related('farm')
        .order_by('farm__name', 'name', 'id')
    ):
        conditions = conditions_by_plot.get(plot.pk, [])
        summaries.append(
            {
                'id': plot.pk,
                'name': plot.name,
                'description': plot.description,
                'area_hectares': plot.area_hectares,
                'sensor_count': plot.sensor_count,
                'has_geometry': plot.geometry is not None,
                'farm': plot.farm,
                'latest_reading_at': max(
                    (condition['recorded_at'] for condition in conditions), default=None
                ),
                'conditions': conditions,
                'irrigation': latest_irrigation.get(plot.pk),
            }
        )
    return summaries

