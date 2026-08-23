from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farm.models import Farm, Plot
from farm.serializers import FarmSerializer, PlotDetailSerializer, PlotSerializer
from sensors.models import SemanticKey, WeatherMeasurement


def get_owned_or_404(queryset, **lookup):
    """Fetch a single row from an ownership-scoped queryset, or raise DRF's generic 404.

    Django's `get_object_or_404` names the model in the response body, which would make a
    row that exists but belongs to someone else distinguishable from one that never existed.
    """
    try:
        return queryset.get(**lookup)
    except ObjectDoesNotExist as does_not_exist:
        raise NotFound from does_not_exist


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
        return farm.plots.all()
