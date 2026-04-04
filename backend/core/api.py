from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from core.models import GeneralSiteSettings, SocialMediaSettings
from core.serializers import GeneralSiteSettingsSerializer, SocialMediaSettingsSerializer


class GeneralSiteSettingsAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        instance = GeneralSiteSettings.objects.first()
        serializer = GeneralSiteSettingsSerializer(instance)
        return Response(serializer.data)


class SocialMediaSettingsAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        instance = SocialMediaSettings.objects.first()
        serializer = SocialMediaSettingsSerializer(instance)
        return Response(serializer.data)