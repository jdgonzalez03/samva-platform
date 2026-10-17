import json

from rest_framework import serializers

from predictions.serializers import IrrigationPredictionSerializer
from sensors.serializers import FieldSensorSerializer, HistorySeriesSerializer

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


class PlotConditionSerializer(serializers.Serializer):
    semantic_key = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    value = serializers.FloatField()
    recorded_at = serializers.DateTimeField()
    change_24h = serializers.FloatField(allow_null=True)
    level = serializers.CharField(allow_null=True)
    level_degrees = serializers.DictField(child=serializers.FloatField(), allow_null=True)


class PlotOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    conditions = PlotConditionSerializer(many=True)
    series = HistorySeriesSerializer(many=True)
    sensors = FieldSensorSerializer(many=True)
    irrigation = IrrigationPredictionSerializer(allow_null=True)


class PlotSeriesPointSerializer(serializers.Serializer):
    t = serializers.DateTimeField()
    value = serializers.FloatField()


class PlotVariableSeriesSerializer(serializers.Serializer):
    semantic_key = serializers.CharField()
    points = PlotSeriesPointSerializer(many=True)


class FarmPlotSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    latest_reading_at = serializers.DateTimeField(allow_null=True)
    conditions = PlotConditionSerializer(many=True)
    series = PlotVariableSeriesSerializer(many=True)
    irrigation = IrrigationPredictionSerializer(allow_null=True)


class FarmOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    conditions = PlotConditionSerializer(many=True)
    series = HistorySeriesSerializer(many=True)
    plots = FarmPlotSummarySerializer(many=True)
    sensors = FieldSensorSerializer(many=True)


class PlotSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    area_hectares = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    sensor_count = serializers.IntegerField()
    has_geometry = serializers.BooleanField()
    farm = FarmSummarySerializer()
    latest_reading_at = serializers.DateTimeField(allow_null=True)
    conditions = PlotConditionSerializer(many=True)
    irrigation = IrrigationPredictionSerializer(allow_null=True)

