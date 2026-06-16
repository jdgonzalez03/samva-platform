from rest_framework import serializers

from .models import Farmer


class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'document_type',
            'document_number', 
            'gender', 
            'phone_number', 
            'city',
            'department', 
            'address', 
            'avatar', 
            'is_active',
        ]
