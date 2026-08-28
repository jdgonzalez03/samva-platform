from django.db import models
from django.db.models import Avg, Count, F, Func, Value

from sensors.constants import BUCKET_TIERS, VARIABLE_COLUMNS, WIDEST_BUCKET
from sensors.models import SensorMeasurement


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


def build_series(measurements, range_start, bucket_size):
    """Group bucket averages into one series per environmental variable.

    A single aggregate statement covers every variable of the plot; the regrouping below is
    one Python pass over its rows, so the query count never grows with the variable count.
    """
    rows = (
        measurements.annotate(
            bucket=DateBin(
                Value(bucket_size, output_field=models.DurationField()),
                F('recorded_at'),
                Value(range_start),
            )
        )
        .values('bucket', *VARIABLE_COLUMNS)
        .annotate(average=Avg('value'), sample_count=Count('id'))
        .order_by('sensor_variable__env_variable__name', 'bucket')
    )

    series_by_variable = {}
    for row in rows:
        variable_id = row['sensor_variable__env_variable_id']
        series = series_by_variable.get(variable_id)
        if series is None:
            series = {
                'variable_id': variable_id,
                'semantic_key': row['sensor_variable__env_variable__semantic_key'],
                'name': row['sensor_variable__env_variable__name'],
                'unit': row['sensor_variable__env_variable__unit'],
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
