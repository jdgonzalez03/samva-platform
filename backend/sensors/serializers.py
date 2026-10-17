from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from sensors.constants import (
    DEFAULT_HISTORY_RANGE_DAYS,
    HISTORY_MAX_RANGE_DAYS,
    INGEST_MAX_CLOCK_SKEW,
    SENSOR_OFFLINE_AFTER,
    STATION_STATUSES,
)
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    ProviderWeatherStationChoices,
    SemanticKey,
    SensorMeasurement,
    WeatherMeasurement,
)


class HistoryRangeFilterSerializer(serializers.Serializer):
    """The `variable` + date range params shared by the sensor and station history endpoints.

    Hand-rolled instead of a `django-filter` FilterSet because the range needs cross-field
    validation a FilterSet cannot express, and because `DEFAULT_FILTER_BACKENDS` is global —
    turning it on would reach the `farm` endpoints too.
    """

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


class SensorHistoryFilterSerializer(HistoryRangeFilterSerializer):
    plot = serializers.IntegerField(required=False, allow_null=True)


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


class TimezoneAwareDateTimeField(serializers.DateTimeField):
    """Rejects a timestamp without an offset instead of assuming the server's timezone.

    A device that omits it is usually sending local time, which would be stored hours off.
    """

    default_error_messages = {"naive": "Datetime must include a timezone offset."}

    def enforce_timezone(self, value):
        if timezone.is_naive(value):
            self.fail("naive")
        return super().enforce_timezone(value)


class IngestReadingSerializer(serializers.Serializer):
    variable = serializers.ChoiceField(
        choices=SemanticKey.choices,
        help_text="Semantic key of a variable mapped to this sensor.",
    )
    value = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        allow_null=True,
        help_text="Measured value, up to 4 decimals; null when the probe failed.",
    )


class SensorIngestSerializer(serializers.Serializer):
    serial_number = serializers.CharField(
        max_length=100,
        help_text="Hardware serial the sensor was registered with.",
    )
    recorded_at = TimezoneAwareDateTimeField(
        help_text="When the sensor measured (not when it sends), ISO 8601 with an offset.",
    )
    readings = IngestReadingSerializer(
        many=True,
        allow_empty=False,
        help_text="One entry per variable measured at recorded_at; each variable once.",
    )

    def validate_recorded_at(self, recorded_at):
        if recorded_at > timezone.now() + INGEST_MAX_CLOCK_SKEW:
            raise serializers.ValidationError("recorded_at must not be in the future.")
        return recorded_at

    def validate_readings(self, readings):
        variables = [reading["variable"] for reading in readings]
        if len(variables) != len(set(variables)):
            raise serializers.ValidationError("Each variable may appear only once.")
        return readings


class SensorIngestResultSerializer(serializers.Serializer):
    created = serializers.IntegerField(help_text="Variables stored by this request.")
    duplicates = serializers.IntegerField(
        help_text="Variables already stored for this instant, typically from a retry."
    )


class SensorVariableSerializer(serializers.Serializer):
    semantic_key = serializers.CharField(source="env_variable.semantic_key")
    name = serializers.CharField(source="env_variable.name")
    unit = serializers.CharField(source="env_variable.unit")


class FieldSensorSerializer(serializers.ModelSerializer):
    plot_id = serializers.IntegerField()
    plot_name = serializers.CharField(source="plot.name")
    variables = SensorVariableSerializer(source="sensor_variables", many=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = FieldSensor
        fields = [
            "id",
            "name",
            "serial_number",
            "plot_id",
            "plot_name",
            "is_active",
            "installed_at",
            "last_seen_at",
            "status",
            "variables",
        ]

    def get_status(self, sensor) -> str:
        if not sensor.is_active:
            return "inactive"
        if sensor.last_seen_at is None:
            return "never_seen"
        if timezone.now() - sensor.last_seen_at > SENSOR_OFFLINE_AFTER:
            return "offline"
        return "online"


class StationLatestSerializer(serializers.Serializer):
    variable_id = serializers.IntegerField()
    semantic_key = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()
    value = serializers.FloatField()
    recorded_at = serializers.DateTimeField()


class SparklinePointSerializer(serializers.Serializer):
    t = serializers.DateTimeField()
    value = serializers.FloatField()


class StationSparklineSerializer(serializers.Serializer):
    semantic_key = serializers.CharField()
    unit = serializers.CharField()
    points = SparklinePointSerializer(many=True)


class WeatherStationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    farm_id = serializers.IntegerField()
    name = serializers.CharField()
    provider = serializers.ChoiceField(choices=ProviderWeatherStationChoices.choices)
    is_active = serializers.BooleanField()
    status = serializers.ChoiceField(choices=STATION_STATUSES)
    last_reading_at = serializers.DateTimeField(allow_null=True)
    latest = StationLatestSerializer(many=True)
    sparkline = StationSparklineSerializer(allow_null=True)


class WeatherStationVariableSerializer(serializers.Serializer):
    variable_id = serializers.IntegerField()
    semantic_key = serializers.CharField()
    name = serializers.CharField()
    unit = serializers.CharField()


class WeatherStationDetailSerializer(WeatherStationSerializer):
    variables = WeatherStationVariableSerializer(many=True)


class StationReadingSerializer(serializers.ModelSerializer):
    recorded_at = serializers.DateTimeField(source="snapshot.recorded_at")
    variable_id = serializers.IntegerField(source="station_variable.env_variable_id")
    semantic_key = serializers.CharField(source="station_variable.env_variable.semantic_key")
    variable_name = serializers.CharField(source="station_variable.env_variable.name")
    unit = serializers.CharField(source="station_variable.env_variable.unit")
    value = serializers.FloatField()

    class Meta:
        model = WeatherMeasurement
        fields = [
            "id",
            "recorded_at",
            "variable_id",
            "semantic_key",
            "variable_name",
            "value",
            "unit",
        ]


class StationReadingPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = StationReadingSerializer(many=True)
