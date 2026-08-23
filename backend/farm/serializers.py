import json

from rest_framework import serializers

from .models import Farm, Plot


def to_geojson(value):
    """Render a GEOS geometry as plain GeoJSON `{type, coordinates}` in [lng, lat] order."""
    if value is None:
        return None
    geojson = json.loads(value.geojson)
    geojson.pop('crs', None)
    return geojson


class FarmSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    boundary = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = [
            'id',
            'name',
            'address',
            'location',
            'boundary',
            'created_at',
        ]

    def get_location(self, farm):
        return to_geojson(farm.location)

    def get_boundary(self, farm):
        return to_geojson(farm.boundary)


class FarmSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = [
            'id',
            'name',
        ]


class PlotSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()
    centroid = serializers.SerializerMethodField()
    label_point = serializers.SerializerMethodField()
    sensor_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Plot
        fields = [
            'id',
            'name',
            'description',
            'geometry',
            'centroid',
            'label_point',
            'area_hectares',
            'sensor_count',
        ]

    def get_geometry(self, plot):
        return to_geojson(plot.geometry)

    def get_centroid(self, plot):
        return to_geojson(plot.centroid)

    def get_label_point(self, plot):
        # A centroid is not guaranteed to lie inside a concave polygon (an L, a U, a crescent);
        # point_on_surface is. Derived from the already-loaded geometry, so it costs no query.
        if plot.geometry is None:
            return None
        return to_geojson(plot.geometry.point_on_surface)


class PlotDetailSerializer(PlotSerializer):
    farm = FarmSummarySerializer(read_only=True)

    class Meta(PlotSerializer.Meta):
        # Subclassing is what guarantees the shared fields cannot drift from a list row.
        fields = PlotSerializer.Meta.fields + [
            'farm',
            'created_at',
            'updated_at',
        ]
