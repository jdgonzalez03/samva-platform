from django.db import models
from django.db.models import Avg, Count, F, Func, Value

from sensors.constants import (
    BUCKET_TIERS,
    STATION_SPARKLINE_BUCKET,
    STATION_SPARKLINE_SPAN,
    VARIABLE_COLUMNS,
    WIDEST_BUCKET,
)
from sensors.models import SensorMeasurement, WeatherMeasurement

SENSOR_VARIABLE_FIELD = 'sensor_variable__env_variable'


class DateBin(Func):
    """PostgreSQL `date_bin(stride, source, origin)`.

    The origin is the requested range start, so bucket edges line up with the window the
    chart asked for instead of drifting with an arbitrary epoch.
    """

    function = 'date_bin'
    arity = 3
    output_field = models.DateTimeField()



def bucket_size_for(span):
    """Bucket width that keeps a single series under ~200 points for the given span."""
    for upper_bound, bucket_size in BUCKET_TIERS:
        if span <= upper_bound:
            return bucket_size
    return WIDEST_BUCKET


def history_measurements(farm, plot, filters):
    """Base queryset shared by every history endpoint, already scoped and filtered."""
    if plot is None:
        scope = {'sensor_variable__sensor__plot__farm_id': farm.pk}
    else:
        scope = {'sensor_variable__sensor__plot_id': plot.pk}

    measurements = SensorMeasurement.objects.filter(
        sensor_variable__sensor__is_active=True,
        value__isnull=False,
        recorded_at__gte=filters['date_from'],
        recorded_at__lt=filters['date_to'],
        **scope,
    )

    semantic_key = filters.get('variable')
    if semantic_key:
        return measurements.filter(sensor_variable__env_variable__semantic_key=semantic_key)
    return measurements


def build_series(
    measurements,
    range_start,
    bucket_size,
    time_field='recorded_at',
    variable_field=SENSOR_VARIABLE_FIELD,
):
    """Group bucket averages into one series per environmental variable.

    A single aggregate statement covers every variable of the plot; the regrouping below is
    one Python pass over its rows, so the query count never grows with the variable count.
    `time_field`/`variable_field` are the lookups from the measurement model to its
    timestamp and its `EnvironmentalVariable`, so field sensors and weather stations share it.
    """
    variable_id_column = f'{variable_field}_id'
    rows = (
        measurements.annotate(
            bucket=DateBin(
                Value(bucket_size, output_field=models.DurationField()),
                F(time_field),
                Value(range_start),
            )
        )
        .values(
            'bucket',
            variable_id_column,
            f'{variable_field}__semantic_key',
            f'{variable_field}__name',
            f'{variable_field}__unit',
        )
        .annotate(average=Avg('value'), sample_count=Count('id'))
        .order_by(f'{variable_field}__name', 'bucket')
    )

    series_by_variable = {}
    for row in rows:
        variable_id = row[variable_id_column]
        series = series_by_variable.get(variable_id)
        if series is None:
            series = {
                'variable_id': variable_id,
                'semantic_key': row[f'{variable_field}__semantic_key'],
                'name': row[f'{variable_field}__name'],
                'unit': row[f'{variable_field}__unit'],
                'bucket_seconds': int(bucket_size.total_seconds()),
                'points': [],
            }
            series_by_variable[variable_id] = series
        # Empty buckets are absent rather than zero-filled: the frontend rebuilds the gaps
        # from `bucket_seconds` so the line breaks instead of faking a reading.
        series['points'].append(
            {
                't': row['bucket'],
                'value': float(row['average']),
                'sample_count': row['sample_count'],
            }
        )

    return list(series_by_variable.values())


def build_plot_averages(measurements):
    """One average per (plot, variable) pair over the whole range, in a single statement."""
    return (
        measurements.values(
            'sensor_variable__sensor__plot_id',
            'sensor_variable__sensor__plot__name',
            *VARIABLE_COLUMNS,
        )
        .annotate(average=Avg('value'), sample_count=Count('id'))
        .order_by(
            'sensor_variable__sensor__plot__name',
            'sensor_variable__env_variable__name',
        )
    )


def station_measurements(station, filters):
    """Base queryset shared by the station history endpoints, already scoped and filtered.

    Only active station variables count, matching the `variables` list of the station detail.
    The station's own `is_active` is not a filter: its stored history stays readable.
    """
    measurements = WeatherMeasurement.objects.filter(
        station_variable__station=station,
        station_variable__is_active=True,
        value__isnull=False,
        snapshot__recorded_at__gte=filters['date_from'],
        snapshot__recorded_at__lt=filters['date_to'],
    )

    semantic_key = filters.get('variable')
    if semantic_key:
        return measurements.filter(station_variable__env_variable__semantic_key=semantic_key)
    return measurements


def latest_station_values(station_variable_ids):
    """`{station_variable_id: (value, recorded_at)}` of the newest non-null value of each."""
    # PostgreSQL `DISTINCT ON`: one row per station variable in a single query.
    rows = (
        WeatherMeasurement.objects.filter(
            station_variable_id__in=station_variable_ids,
            value__isnull=False,
        )
        .order_by('station_variable_id', '-snapshot__recorded_at')
        .distinct('station_variable_id')
        .values_list('station_variable_id', 'value', 'snapshot__recorded_at')
    )
    return {
        station_variable_id: (float(value), recorded_at)
        for station_variable_id, value, recorded_at in rows
    }


def sparkline_start(now):
    """Start of the sparkline window: hour-aligned, so it covers at least the full span."""
    return (now - STATION_SPARKLINE_SPAN).replace(minute=0, second=0, microsecond=0)


def station_sparkline_points(station_variable_ids, now):
    """`{station_variable_id: [{t, value}]}` of hourly averages since `sparkline_start`."""
    range_start = sparkline_start(now)
    rows = (
        WeatherMeasurement.objects.filter(
            station_variable_id__in=station_variable_ids,
            value__isnull=False,
            snapshot__recorded_at__gte=range_start,
        )
        .annotate(
            bucket=DateBin(
                Value(STATION_SPARKLINE_BUCKET, output_field=models.DurationField()),
                F('snapshot__recorded_at'),
                Value(range_start),
            )
        )
        .values('station_variable_id', 'bucket')
        .annotate(average=Avg('value'))
        .order_by('station_variable_id', 'bucket')
    )

    points_by_variable = {}
    for row in rows:
        points_by_variable.setdefault(row['station_variable_id'], []).append(
            {'t': row['bucket'], 'value': float(row['average'])}
        )
    return points_by_variable
