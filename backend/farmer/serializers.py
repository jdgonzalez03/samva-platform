from rest_framework import serializers

from .models import Farmer, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'nit',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class FarmerSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)

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
            'organization',
            'created_at',
        ]


class FarmerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = [
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
        ]
