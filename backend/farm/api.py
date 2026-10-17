from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_owned_or_404
from farm.models import Farm, Plot
from farm.serializers import (
    FarmOverviewSerializer,
    FarmSerializer,
    PlotDetailSerializer,
    PlotOverviewSerializer,
    PlotSerializer,
    PlotSummarySerializer,
)
from farm.utils import build_farm_overview, build_plot_overview, build_plot_summaries


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


class PlotOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PlotOverviewSerializer)
    def get(self, request, plot_id):
        plot = get_owned_or_404(
            Plot.objects.select_related('farm'),
            pk=plot_id,
            farm__owner__user=request.user,
        )
        return Response(PlotOverviewSerializer(build_plot_overview(plot)).data)


class FarmOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=FarmOverviewSerializer)
    def get(self, request, farm_id):
        farm = get_owned_or_404(Farm.objects.all(), pk=farm_id, owner__user=request.user)
        return Response(FarmOverviewSerializer(build_farm_overview(farm)).data)


class PlotSummaryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PlotSummarySerializer(many=True))
    def get(self, request):
        return Response(PlotSummarySerializer(build_plot_summaries(request.user), many=True).data)

