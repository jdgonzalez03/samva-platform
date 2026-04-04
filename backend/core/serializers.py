from rest_framework import serializers

from core.models import GeneralSiteSettings, SocialMediaSettings


class GeneralSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralSiteSettings
        fields = ["contact_email", "contact_phone", "location"]


class SocialMediaSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaSettings
        fields = ["facebook", "twitter", "instagram"]
