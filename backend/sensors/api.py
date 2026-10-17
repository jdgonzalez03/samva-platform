import logging

from django.db.models import Prefetch
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, pagination, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_owned_or_404
from farm.models import Farm
from sensors.aggregation import (
    bucket_size_for,
    build_plot_averages,
    build_series,
    history_measurements,
    station_measurements,
)
from sensors.authentication import (
    ApiKeyAuthentication,
    ApiKeyRateThrottle,
    IsActiveApiKeyOwner,
)
from sensors.constants import (
    READING_ORDER,
    SENSOR_CSV_COLUMNS,
    STATION_CSV_COLUMNS,
    STATION_READING_ORDER,
    STATION_TIME_FIELD,
    STATION_VARIABLE_FIELD,
)
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    WeatherStation,
)
from sensors.openapi import (
    INGEST_DESCRIPTION,
    INGEST_REQUEST_EXAMPLES,
    INGEST_RESPONSES,
    INGEST_TAG,
    STATION_DETAIL_DESCRIPTION,
    STATION_DETAIL_RESPONSES,
    STATION_EXPORT_DESCRIPTION,
    STATION_HISTORY_PARAMETERS,
    STATION_LIST_DESCRIPTION,
    STATION_LIST_RESPONSES,
    STATION_PAGE_PARAMETERS,
    STATION_READINGS_RESPONSES,
    STATION_SERIES_DESCRIPTION,
    STATION_SERIES_RESPONSES,
    STATIONS_TAG,
    station_export_responses,
)
from sensors.serializers import (
    FieldSensorSerializer,
    HistorySeriesSerializer,
    HistoryVariableSerializer,
    PlotAverageSerializer,
    SensorIngestResultSerializer,
    SensorIngestSerializer,
    SensorReadingSerializer,
    StationReadingSerializer,
    WeatherStationDetailSerializer,
    WeatherStationSerializer,
)
from sensors.utils import (
    attachment_headers,
    build_station_cards,
    export_cap_error,
    export_filename,
    export_rows,
    history_scope,
    ingest_reading,
    sensor_export_records,
    station_cards_queryset,
    station_export_filename,
    station_export_records,
    station_export_rows,
    station_history_scope,
    stream_csv,
    stream_json,
)

logger = logging.getLogger(__name__)


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
            stream_csv(SENSOR_CSV_COLUMNS, sensor_export_records(export_rows(farm, plot, filters))),
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
            stream_json(sensor_export_records(export_rows(farm, plot, filters))),
            content_type='application/json',
            headers=attachment_headers(export_filename(farm, filters, 'json')),
        )


class SensorIngestAPIView(APIView):
    """Public entry point for field sensors, authenticated by the owner's `X-API-Key`."""

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsActiveApiKeyOwner]
    throttle_classes = [ApiKeyRateThrottle]

    @extend_schema(
        tags=[INGEST_TAG],
        summary="Push a sensor reading",
        description=INGEST_DESCRIPTION,
        request=SensorIngestSerializer,
        responses=INGEST_RESPONSES,
        examples=INGEST_REQUEST_EXAMPLES,
    )
    def post(self, request):
        serializer = SensorIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created, duplicates = ingest_reading(request.auth, serializer.validated_data)
        return Response(
            SensorIngestResultSerializer({"created": created, "duplicates": duplicates}).data,
            status=status.HTTP_201_CREATED,
        )

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        # Devices have no screen, so this log is the only place a misconfigured one shows
        # up. The key itself is never logged: it would hand the account to log readers.
        serial_number = None
        if isinstance(self.request.data, dict):
            serial_number = self.request.data.get("serial_number")
        logger.warning(
            "Sensor ingest rejected: status=%s farmer=%s serial=%s detail=%s",
            response.status_code,
            getattr(self.request.auth, "pk", None),
            serial_number,
            response.data,
        )
        return response


class FieldSensorListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FieldSensorSerializer

    def get_queryset(self):
        farm = get_owned_or_404(
            Farm.objects.all(), pk=self.kwargs["farm_id"], owner__user=self.request.user
        )
        return (
            FieldSensor.objects.filter(plot__farm=farm)
            .select_related("plot")
            .prefetch_related(
                Prefetch(
                    "sensor_variables",
                    queryset=FieldSensorVariable.objects.select_related(
                        "env_variable"
                    ).order_by("env_variable__name"),
                )
            )
            .order_by("plot__name", "name", "id")
        )


class WeatherStationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="List a farm's weather stations",
        description=STATION_LIST_DESCRIPTION,
        responses=STATION_LIST_RESPONSES,
    )
    def get(self, request, farm_id):
        farm = get_owned_or_404(Farm.objects.all(), pk=farm_id, owner__user=request.user)
        stations = station_cards_queryset(WeatherStation.objects.filter(farm=farm))
        return Response(WeatherStationSerializer(build_station_cards(stations), many=True).data)


class WeatherStationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="Get a weather station",
        description=STATION_DETAIL_DESCRIPTION,
        responses=STATION_DETAIL_RESPONSES,
    )
    def get(self, request, station_id):
        stations = station_cards_queryset(
            WeatherStation.objects.filter(pk=station_id, farm__owner__user=request.user)
        )
        cards = build_station_cards(stations, with_variables=True)
        if not cards:
            raise NotFound
        return Response(WeatherStationDetailSerializer(cards[0]).data)


class WeatherStationSeriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="Bucketed series of a weather station",
        description=STATION_SERIES_DESCRIPTION,
        parameters=STATION_HISTORY_PARAMETERS,
        responses=STATION_SERIES_RESPONSES,
    )
    def get(self, request, station_id):
        station, filters = station_history_scope(request, station_id)

        bucket_size = bucket_size_for(filters['date_to'] - filters['date_from'])
        series = build_series(
            station_measurements(station, filters),
            filters['date_from'],
            bucket_size,
            time_field=STATION_TIME_FIELD,
            variable_field=STATION_VARIABLE_FIELD,
        )
        return Response(HistorySeriesSerializer(series, many=True).data)


class WeatherStationReadingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="Paginated readings of a weather station",
        parameters=[*STATION_HISTORY_PARAMETERS, *STATION_PAGE_PARAMETERS],
        responses=STATION_READINGS_RESPONSES,
    )
    def get(self, request, station_id):
        station, filters = station_history_scope(request, station_id)

        readings = (
            station_measurements(station, filters)
            .select_related('snapshot', 'station_variable__env_variable')
            .order_by(*STATION_READING_ORDER)
        )
        paginator = SensorHistoryPagination()
        page = paginator.paginate_queryset(readings, request, view=self)
        return paginator.get_paginated_response(StationReadingSerializer(page, many=True).data)


class WeatherStationCsvExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="Export a weather station's readings as CSV",
        description=STATION_EXPORT_DESCRIPTION,
        parameters=STATION_HISTORY_PARAMETERS,
        responses=station_export_responses('text/csv'),
    )
    def get(self, request, station_id):
        station, filters = station_history_scope(request, station_id)

        cap_error = export_cap_error(station_measurements(station, filters))
        if cap_error is not None:
            return cap_error

        return StreamingHttpResponse(
            stream_csv(
                STATION_CSV_COLUMNS,
                station_export_records(station_export_rows(station, filters)),
            ),
            content_type='text/csv; charset=utf-8',
            headers=attachment_headers(station_export_filename(station, filters, 'csv')),
        )


class WeatherStationJsonExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[STATIONS_TAG],
        summary="Export a weather station's readings as JSON",
        description=STATION_EXPORT_DESCRIPTION,
        parameters=STATION_HISTORY_PARAMETERS,
        responses=station_export_responses('application/json'),
    )
    def get(self, request, station_id):
        station, filters = station_history_scope(request, station_id)

        cap_error = export_cap_error(station_measurements(station, filters))
        if cap_error is not None:
            return cap_error

        return StreamingHttpResponse(
            stream_json(station_export_records(station_export_rows(station, filters))),
            content_type='application/json',
            headers=attachment_headers(station_export_filename(station, filters, 'json')),
        )
