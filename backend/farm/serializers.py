from rest_framework import serializers

from .models import Farm, Plot


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = [
            'id',
            'name',
            'address',
            'created_at',
        ]


class PlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plot
        fields = [
            'id',
            'name',
            'description',
            'area_hectares',
        ]
