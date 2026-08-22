from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from farm.models import Farm
from farm.serializers import FarmSerializer, PlotSerializer


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
        farm = get_object_or_404(
            Farm,
            pk=self.kwargs['farm_id'],
            owner__user=self.request.user,
        )
        return farm.plots.all()
