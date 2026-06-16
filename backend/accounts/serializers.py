from django.contrib.auth import get_user_model
from farmer.serializers import FarmerSerializer
from rest_framework import serializers


User = get_user_model()


class MeSerializer(serializers.ModelSerializer):
    farmer = FarmerSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'farmer']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
