from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_owned_or_404
from farm.models import Farm, Plot
from farm.serializers import FarmSerializer, PlotDetailSerializer, PlotSerializer
from sensors.models import SemanticKey, WeatherMeasurement


class FarmListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FarmSerializer

    def get_queryset(self):
        # Scoped through the `owner__user` lookup rather than `request.user.farmer`
        # so a user without a Farmer row gets an empty list instead of a 500.
        return Farm.objects.filter(owner__user=self.request.user)


class FarmPlotListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlotSerializer

    def get_queryset(self):
        # Ownership is part of the lookup: a farm owned by someone else 404s
        # instead of returning an empty list, which would leak its existence.
        farm = get_owned_or_404(
            Farm.objects.all(),
            pk=self.kwargs['farm_id'],
            owner__user=self.request.user,
        )
        return farm.plots.with_sensor_count()


class PlotDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlotDetailSerializer

    def get_object(self):
        return get_owned_or_404(
            Plot.objects.with_sensor_count().select_related('farm'),
            pk=self.kwargs['plot_id'],
            farm__owner__user=self.request.user,
        )


class FarmWeatherAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        farm = get_owned_or_404(Farm.objects.all(), pk=farm_id, owner__user=request.user)

        # One `DISTINCT ON` (PostgreSQL-only, and this project is PostGIS) keeps the
        # endpoint at a constant two queries instead of O(stations x variables).
        latest_per_key = (
            WeatherMeasurement.objects.filter(
                station_variable__station__farm=farm,
                station_variable__station__is_active=True,
                station_variable__is_active=True,
                value__isnull=False,
            )
            .exclude(station_variable__env_variable__semantic_key=SemanticKey.OTHER)
            .select_related('snapshot', 'station_variable__env_variable')
            .order_by(
                'station_variable__env_variable__semantic_key',
                '-snapshot__recorded_at',
                '-station_variable__station_id',
            )
            .distinct('station_variable__env_variable__semantic_key')
        )

        # A key with no usable reading is omitted entirely: absence is the only
        # "no data" signal on the wire, so a farm without readings returns `{}`.
        return Response(
            {
                measurement.station_variable.env_variable.semantic_key: {
                    'value': float(measurement.value),
                    'unit': measurement.station_variable.env_variable.unit,
                    'recorded_at': measurement.snapshot.recorded_at,
                }
                for measurement in latest_per_key
            }
        )
