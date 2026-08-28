from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from sensors.constants import DEFAULT_HISTORY_RANGE_DAYS, HISTORY_MAX_RANGE_DAYS
from sensors.models import EnvironmentalVariable, SemanticKey, SensorMeasurement


class SensorHistoryFilterSerializer(serializers.Serializer):
    """The query params shared by every history endpoint.

    Hand-rolled instead of a `django-filter` FilterSet because three of the four params need
    cross-field validation a FilterSet cannot express, and because `DEFAULT_FILTER_BACKENDS`
    is global — turning it on would reach the `farm` endpoints too.
    """

    plot = serializers.IntegerField(required=False, allow_null=True)
    variable = serializers.ChoiceField(choices=SemanticKey.choices, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)

    def validate(self, attributes):
        date_to = attributes.get("date_to") or timezone.now()
        date_from = attributes.get("date_from")
        if date_from is None:
            date_from = date_to - timedelta(days=DEFAULT_HISTORY_RANGE_DAYS)

        if date_from >= date_to:
            raise serializers.ValidationError(
                {"date_from": ["date_from must be earlier than date_to."]}
            )
        if date_to - date_from > timedelta(days=HISTORY_MAX_RANGE_DAYS):
            raise serializers.ValidationError(
                {
                    "date_from": [
                        f"The selected range must not exceed {HISTORY_MAX_RANGE_DAYS} days."
                    ]
                }
            )

        attributes["date_from"] = date_from
        attributes["date_to"] = date_to
        return attributes


class HistoryVariableSerializer(serializers.ModelSerializer):
    variable_id = serializers.IntegerField(source="id")

    class Meta:
        model = EnvironmentalVariable
        fields = ["variable_id", "semantic_key", "name", "unit"]


class SensorReadingSerializer(serializers.ModelSerializer):
    plot_id = serializers.IntegerField(source="sensor_variable.sensor.plot_id")
    plot_name = serializers.CharField(source="sensor_variable.sensor.plot.name")
    sensor_id = serializers.IntegerField(source="sensor_variable.sensor_id")
    sensor_name = serializers.CharField(source="sensor_variable.sensor.name")
    variable_id = serializers.IntegerField(source="sensor_variable.env_variable_id")
    semantic_key = serializers.CharField(source="sensor_variable.env_variable.semantic_key")
    variable_name = serializers.CharField(source="sensor_variable.env_variable.name")
    unit = serializers.CharField(source="sensor_variable.env_variable.unit")
    # A plain DecimalField would render `27.4133` as the string "27.4133"; charts and the
    # CSV/JSON exports all expect a JSON number.
    value = serializers.FloatField()

    class Meta:
        model = SensorMeasurement
        fields = [
            "id",
            "recorded_at",
            "plot_id",
            "plot_name",
            "sensor_id",
            "sensor_name",
            "variable_id",
            "semantic_key",
            "variable_name",
            "value",
            "unit",
        ]


class SeriesPointSerializer(serializers.Serializer):
    t = serializers.DateTimeField()
    value = serializers.FloatField()
    sample_count = serializers.IntegerField()


class HistorySeriesSerializer(serializers.Serializer):
    variable_id = serializers.IntegerField()
    semantic_key = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    bucket_seconds = serializers.IntegerField()
    points = SeriesPointSerializer(many=True)


class PlotAverageSerializer(serializers.Serializer):
    plot_id = serializers.IntegerField(source="sensor_variable__sensor__plot_id")
    plot_name = serializers.CharField(source="sensor_variable__sensor__plot__name")
    variable_id = serializers.IntegerField(source="sensor_variable__env_variable_id")
    semantic_key = serializers.CharField(source="sensor_variable__env_variable__semantic_key")
    variable_name = serializers.CharField(source="sensor_variable__env_variable__name")
    unit = serializers.CharField(source="sensor_variable__env_variable__unit")
    average = serializers.FloatField()
    sample_count = serializers.IntegerField()
