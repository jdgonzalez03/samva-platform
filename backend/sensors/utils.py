import csv
import json
from datetime import UTC
from urllib.parse import quote

from django.db.models import Max, Prefetch
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response

from core.utils import get_owned_or_404
from farm.models import Farm, Plot
from sensors.aggregation import (
    history_measurements,
    latest_station_values,
    station_measurements,
    station_sparkline_points,
)
from sensors.constants import (
    BOM_UTF8,
    EXPORT_COLUMNS,
    HISTORY_EXPORT_ROW_CAP,
    READING_ORDER,
    STATION_EXPORT_COLUMNS,
    STATION_READING_ORDER,
    STATION_SPARKLINE_KEY,
    STATION_STALE_AFTER,
)
from sensors.models import (
    FieldSensor,
    SensorMeasurement,
    WeatherStation,
    WeatherStationVariableConfiguration,
)
from sensors.serializers import HistoryRangeFilterSerializer, SensorHistoryFilterSerializer


def resolve_history_scope(request, farm_id, plot_id):
    """Return `(farm, plot)` for the route, enforcing ownership; `plot` is None when absent.

    Both branches cost exactly one query. A plot the user owns but that hangs off a
    different farm than `farm_id` 404s, so the route cannot be used to read across farms.
    """
    if plot_id is None:
        farm = get_owned_or_404(Farm.objects.all(), pk=farm_id, owner__user=request.user)
        return farm, None

    plot = get_owned_or_404(
        Plot.objects.select_related('farm'),
        pk=plot_id,
        farm_id=farm_id,
        farm__owner__user=request.user,
    )
    return plot.farm, plot


def history_scope(request, farm_id):
    """Validate the shared query params, then resolve the owned farm/plot they point at."""
    filters = SensorHistoryFilterSerializer(data=request.query_params)
    filters.is_valid(raise_exception=True)
    farm, plot = resolve_history_scope(request, farm_id, filters.validated_data.get('plot'))
    return farm, plot, filters.validated_data


def iso_utc(moment):
    return moment.astimezone(UTC).isoformat().replace('+00:00', 'Z')


class Echo:
    """File-like sink whose `write` returns the rendered line instead of buffering it."""

    def write(self, value):
        return value


def export_rows(farm, plot, filters):
    return (
        history_measurements(farm, plot, filters)
        .order_by(*READING_ORDER)
        .values_list(*EXPORT_COLUMNS)
        .iterator(chunk_size=2000)
    )


def history_filename(prefix, subject_name, filters, extension):
    return (
        f'{prefix}-{slugify(subject_name)}-'
        f'{filters["date_from"]:%Y%m%d}_{filters["date_to"]:%Y%m%d}.{extension}'
    )


def export_filename(farm, filters, extension):
    return history_filename('historial-sensores', farm.name, filters, extension)


def attachment_headers(filename):
    return {
        'Content-Disposition': (
            f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        )
    }


def export_cap_error(measurements):
    """Return the 400 body when the filtered set is too large to export, otherwise None."""
    row_count = measurements.count()
    if row_count <= HISTORY_EXPORT_ROW_CAP:
        return None

    # Refusing beats truncating: a silently cut file is a data-integrity bug the user cannot
    # see, so the count and the limit travel back to make the message actionable.
    return Response(
        {
            'detail': 'El rango seleccionado supera el máximo exportable.',
            'code': 'export_too_large',
            'count': row_count,
            'limit': HISTORY_EXPORT_ROW_CAP,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def sensor_export_records(rows):
    for (
        recorded_at,
        plot_id,
        plot_name,
        sensor_id,
        sensor_name,
        variable_id,
        semantic_key,
        variable_name,
        value,
        unit,
    ) in rows:
        yield {
            'recorded_at': iso_utc(recorded_at),
            'plot_id': plot_id,
            'plot_name': plot_name,
            'sensor_id': sensor_id,
            'sensor_name': sensor_name,
            'variable_id': variable_id,
            'semantic_key': semantic_key,
            'variable_name': variable_name,
            'value': float(value),
            'unit': unit,
        }


def stream_csv(columns, records):
    """CSV of `records`, one column per `(title, record key)` pair in `columns`."""
    writer = csv.writer(Echo())
    yield BOM_UTF8
    yield writer.writerow([title for title, _key in columns])
    for record in records:
        yield writer.writerow([record[key] for _title, key in columns])


def stream_json(records):
    # Assembled chunk by chunk rather than through `JsonResponse`, which would hold the
    # whole export in memory before sending a byte.
    yield '['
    separator = ''
    for record in records:
        yield separator + json.dumps(record, ensure_ascii=False)
        separator = ','
    yield ']'


def station_history_scope(request, station_id):
    """Validate the range params, then resolve the owned station they apply to."""
    filters = HistoryRangeFilterSerializer(data=request.query_params)
    filters.is_valid(raise_exception=True)
    station = get_owned_or_404(
        WeatherStation.objects.all(), pk=station_id, farm__owner__user=request.user
    )
    return station, filters.validated_data


def station_export_rows(station, filters):
    return (
        station_measurements(station, filters)
        .order_by(*STATION_READING_ORDER)
        .values_list(*STATION_EXPORT_COLUMNS)
        .iterator(chunk_size=2000)
    )


def station_export_records(rows):
    for (
        recorded_at,
        station_id,
        station_name,
        variable_id,
        semantic_key,
        variable_name,
        value,
        unit,
    ) in rows:
        yield {
            'recorded_at': iso_utc(recorded_at),
            'station_id': station_id,
            'station_name': station_name,
            'variable_id': variable_id,
            'semantic_key': semantic_key,
            'variable_name': variable_name,
            'value': float(value),
            'unit': unit,
        }


def station_export_filename(station, filters, extension):
    return history_filename('historial-estacion', station.name, filters, extension)


def station_cards_queryset(stations):
    """`stations` with what a station card needs, fetched in two queries whatever the count."""
    return (
        stations.annotate(last_reading_at=Max('snapshots__recorded_at'))
        .prefetch_related(
            Prefetch(
                'station_variables',
                queryset=WeatherStationVariableConfiguration.objects.filter(is_active=True)
                .select_related('env_variable')
                .order_by('env_variable__name', 'id'),
                to_attr='active_variables',
            )
        )
        .order_by('name', 'id')
    )


def station_status(station, now):
    if not station.is_active:
        return 'inactive'
    if station.last_reading_at is None:
        return 'never_seen'
    if now - station.last_reading_at > STATION_STALE_AFTER:
        return 'stale'
    return 'online'


def sparkline_variable(station):
    for station_variable in station.active_variables:
        if station_variable.env_variable.semantic_key == STATION_SPARKLINE_KEY:
            return station_variable
    return None


def build_station_cards(stations, with_variables=False):
    """One card per station of `station_cards_queryset`, in two more queries at most.

    The latest values and the sparklines of every station come from one batched query each,
    so the cost does not grow with the number of stations or variables.
    """
    stations = list(stations)
    if not stations:
        return []

    now = timezone.now()
    station_variable_ids = [
        station_variable.pk
        for station in stations
        for station_variable in station.active_variables
    ]
    latest_values = latest_station_values(station_variable_ids) if station_variable_ids else {}

    sparkline_variables = {station.pk: sparkline_variable(station) for station in stations}
    sparkline_ids = [variable.pk for variable in sparkline_variables.values() if variable]
    sparkline_points = station_sparkline_points(sparkline_ids, now) if sparkline_ids else {}

    cards = []
    for station in stations:
        latest = []
        for station_variable in station.active_variables:
            if station_variable.pk not in latest_values:
                continue
            value, recorded_at = latest_values[station_variable.pk]
            latest.append(
                {
                    **variable_summary(station_variable),
                    'value': value,
                    'recorded_at': recorded_at,
                }
            )

        sparkline = None
        sparkline_station_variable = sparkline_variables[station.pk]
        if sparkline_station_variable is not None:
            sparkline = {
                'semantic_key': sparkline_station_variable.env_variable.semantic_key,
                'unit': sparkline_station_variable.env_variable.unit,
                'points': sparkline_points.get(sparkline_station_variable.pk, []),
            }

        card = {
            'id': station.pk,
            'farm_id': station.farm_id,
            'name': station.name,
            'provider': station.provider,
            'is_active': station.is_active,
            'status': station_status(station, now),
            'last_reading_at': station.last_reading_at,
            'latest': latest,
            'sparkline': sparkline,
        }
        if with_variables:
            card['variables'] = [
                variable_summary(station_variable) for station_variable in station.active_variables
            ]
        cards.append(card)
    return cards


def variable_summary(station_variable):
    variable = station_variable.env_variable
    return {
        'variable_id': variable.pk,
        'semantic_key': variable.semantic_key,
        'name': variable.name,
        'unit': variable.unit,
    }


def resolve_sensor(serial_number, farmer=None):
    """Return the active sensor registered with `serial_number` and stamp it as seen.

    With a `farmer` the lookup is scoped to their farms (the HTTP path, where the API key
    names the owner); without one it is global (the MQTT path, where the broker
    credentials are the trust boundary and the owner follows from the sensor's plot).
    """
    # Blank is how the admin marks a sensor whose serial is not registered yet, so it must
    # never resolve to one.
    if not serial_number:
        raise exceptions.NotFound("Unknown sensor.")

    sensors = FieldSensor.objects.filter(serial_number=serial_number)
    if farmer is not None:
        # Someone else's serial 404s like an unknown one, so the endpoint cannot be used to
        # probe which serials are registered.
        sensors = sensors.filter(plot__farm__owner=farmer)
    sensor = sensors.first()
    if sensor is None:
        raise exceptions.NotFound("Unknown sensor.")
    if not sensor.is_active:
        raise exceptions.PermissionDenied("This sensor is inactive.")

    # Stamped before validating the variables: a device sending a misconfigured payload is
    # still online, and "last seen" is what tells its owner to go and look at it.
    FieldSensor.objects.filter(pk=sensor.pk).update(last_seen_at=timezone.now())
    return sensor


def ingest_reading(farmer, reading):
    """Store one timestamped reading of one of `farmer`'s sensors (the HTTP ingest path)."""
    return store_reading(resolve_sensor(reading["serial_number"], farmer), reading)


def store_reading(sensor, reading):
    """Store one timestamped reading of `sensor` and return `(created, duplicates)`.

    A resent reading counts as a duplicate rather than an error, so a device that retries
    after a lost response gets a 201 and stops retrying.
    """
    requested_keys = [entry["variable"] for entry in reading["readings"]]
    sensor_variable_ids = {}
    for semantic_key, sensor_variable_id in sensor.sensor_variables.filter(
        env_variable__semantic_key__in=requested_keys
    ).values_list("env_variable__semantic_key", "pk"):
        sensor_variable_ids.setdefault(semantic_key, []).append(sensor_variable_id)

    errors = []
    for semantic_key in requested_keys:
        matches = sensor_variable_ids.get(semantic_key, [])
        if not matches:
            errors.append(f"The sensor does not measure '{semantic_key}'.")
        elif len(matches) > 1:
            errors.append(f"The sensor measures more than one '{semantic_key}' variable.")
    if errors:
        raise serializers.ValidationError({"readings": errors})

    measurements = [
        SensorMeasurement(
            sensor_variable_id=sensor_variable_ids[entry["variable"]][0],
            value=entry["value"],
            recorded_at=reading["recorded_at"],
        )
        for entry in reading["readings"]
    ]
    already_stored = set(
        SensorMeasurement.objects.filter(
            sensor_variable_id__in=[measurement.sensor_variable_id for measurement in measurements],
            recorded_at=reading["recorded_at"],
        ).values_list("sensor_variable_id", flat=True)
    )
    new_measurements = [
        measurement
        for measurement in measurements
        if measurement.sensor_variable_id not in already_stored
    ]
    # `ignore_conflicts` still guards the race where the same reading lands twice between
    # the lookup above and this insert.
    SensorMeasurement.objects.bulk_create(new_measurements, ignore_conflicts=True)
    return len(new_measurements), len(already_stored)
