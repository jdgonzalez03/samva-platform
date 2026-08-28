from django.http import StreamingHttpResponse
from rest_framework import generics, pagination, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sensors.aggregation import (
    bucket_size_for,
    build_plot_averages,
    build_series,
    history_measurements,
)
from sensors.constants import READING_ORDER
from sensors.models import EnvironmentalVariable
from sensors.serializers import (
    HistorySeriesSerializer,
    HistoryVariableSerializer,
    PlotAverageSerializer,
    SensorReadingSerializer,
)
from sensors.utils import (
    attachment_headers,
    export_cap_error,
    export_filename,
    export_rows,
    history_scope,
    stream_csv,
    stream_json,
)


class SensorHistoryPagination(pagination.PageNumberPagination):
    """Page envelope for the readings table.

    Declared per view rather than as `DEFAULT_PAGINATION_CLASS`, which would also wrap the
    unpaginated `farm` list endpoints and break their consumers.
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        # `next`/`previous` are dropped on purpose: DRF builds them as absolute URLs from the
        # request, which under docker resolve to the internal `backend:8000` host, and the
        # pagination control needs a total and a page number rather than a URL.
        return Response(
            {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'results': data,
            }
        )


class SensorHistoryVariablesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm, plot, _filters = history_scope(request, farm_id)

        if plot is None:
            scope = {'field_sensor_variables__sensor__plot__farm_id': farm.pk}
        else:
            scope = {'field_sensor_variables__sensor__plot_id': plot.pk}

        variables = (
            EnvironmentalVariable.objects.filter(
                field_sensor_variables__sensor__is_active=True,
                **scope,
            )
            .distinct()
            .order_by('name')
        )
        return Response(HistoryVariableSerializer(variables, many=True).data)


class SensorHistoryReadingsAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SensorReadingSerializer
    pagination_class = SensorHistoryPagination

    def get_queryset(self):
        farm, plot, filters = history_scope(self.request, self.kwargs['farm_id'])

        # The `-id` tie-break is load bearing, not cosmetic: sensors write every variable of
        # a reading at the same instant, and without it PostgreSQL is free to order the ties
        # differently for page 1 and page 2, so rows repeat or vanish while paging.
        return (
            history_measurements(farm, plot, filters)
            .select_related(
                'sensor_variable__env_variable',
                'sensor_variable__sensor__plot',
            )
            .order_by(*READING_ORDER)
        )


class SensorHistorySeriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm, plot, filters = history_scope(request, farm_id)
        if plot is None:
            raise serializers.ValidationError({'plot': ['This field is required.']})

        bucket_size = bucket_size_for(filters['date_to'] - filters['date_from'])
        series = build_series(
            history_measurements(farm, plot, filters),
            filters['date_from'],
            bucket_size,
        )
        return Response(HistorySeriesSerializer(series, many=True).data)


class SensorHistoryPlotAveragesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm, _plot, filters = history_scope(request, farm_id)

        # This surface compares the plots of a farm against each other, so a `plot` param
        # would empty it out; it is accepted for a uniform cable and then ignored.
        averages = build_plot_averages(history_measurements(farm, None, filters))
        return Response(PlotAverageSerializer(averages, many=True).data)


class SensorHistoryCsvExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm, plot, filters = history_scope(request, farm_id)

        cap_error = export_cap_error(history_measurements(farm, plot, filters))
        if cap_error is not None:
            return cap_error

        return StreamingHttpResponse(
            stream_csv(export_rows(farm, plot, filters)),
            content_type='text/csv; charset=utf-8',
            headers=attachment_headers(export_filename(farm, filters, 'csv')),
        )


class SensorHistoryJsonExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm, plot, filters = history_scope(request, farm_id)

        cap_error = export_cap_error(history_measurements(farm, plot, filters))
        if cap_error is not None:
            return cap_error

        return StreamingHttpResponse(
            stream_json(export_rows(farm, plot, filters)),
            content_type='application/json',
            headers=attachment_headers(export_filename(farm, filters, 'json')),
        )
