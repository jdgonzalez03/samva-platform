from rest_framework import serializers

from predictions.constants import DEFAULT_AVERAGE_HOURS, MAX_AVERAGE_HOURS
from predictions.models import IrrigationPrediction


class IrrigationPredictionRequestSerializer(serializers.Serializer):
    hours = serializers.IntegerField(
        default=DEFAULT_AVERAGE_HOURS, min_value=1, max_value=MAX_AVERAGE_HOURS
    )


class IrrigationPredictionSerializer(serializers.ModelSerializer):
    avg_moisture = serializers.FloatField()
    avg_temperature = serializers.FloatField()
    avg_radiation = serializers.FloatField()
    irrigation_time_minutes = serializers.FloatField()

    class Meta:
        model = IrrigationPrediction
        fields = [
            'id',
            'plot',
            'avg_moisture',
            'avg_temperature',
            'avg_radiation',
            'avg_period_hours',
            'irrigation_time_minutes',
            'output_label',
            'input_memberships',
            'output_activation',
            'clipped_inputs',
            'input_sources',
            'requested_at',
        ]


class PredictionModelSerializer(serializers.Serializer):
    key = serializers.CharField()
    technique = serializers.CharField()
    target = serializers.CharField()


class MissingSensorDataSerializer(serializers.Serializer):
    detail = serializers.CharField()
    missing = serializers.ListField(child=serializers.CharField())
