import csv
import json
from datetime import UTC
from urllib.parse import quote

from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response

from core.utils import get_owned_or_404
from farm.models import Farm, Plot
from sensors.aggregation import history_measurements
from sensors.constants import (
    BOM_UTF8,
    CSV_HEADER,
    EXPORT_COLUMNS,
    HISTORY_EXPORT_ROW_CAP,
    READING_ORDER,
)
from sensors.serializers import SensorHistoryFilterSerializer


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


def export_filename(farm, filters, extension):
    return (
        f'historial-sensores-{slugify(farm.name)}-'
        f'{filters["date_from"]:%Y%m%d}_{filters["date_to"]:%Y%m%d}.{extension}'
    )


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


def stream_csv(rows):
    writer = csv.writer(Echo())
    yield BOM_UTF8
    yield writer.writerow(CSV_HEADER)
    for (
        recorded_at,
        _plot_id,
        plot_name,
        _sensor_id,
        sensor_name,
        _variable_id,
        semantic_key,
        variable_name,
        value,
        unit,
    ) in rows:
        yield writer.writerow(
            [
                iso_utc(recorded_at),
                plot_name,
                sensor_name,
                variable_name,
                semantic_key,
                float(value),
                unit,
            ]
        )


def stream_json(rows):
    # Assembled chunk by chunk rather than through `JsonResponse`, which would hold the
    # whole export in memory before sending a byte.
    yield '['
    separator = ''
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
        payload = {
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
        yield separator + json.dumps(payload, ensure_ascii=False)
        separator = ','
    yield ']'
