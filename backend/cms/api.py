from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from cms.serializers import LandingPageSerializer
from cms.models import LandingPage

class LandingPageAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            instance = LandingPage.objects.first()
            if not instance: 
                return Response({"detail": "Landing page not found"}, status=404)
            serializer = LandingPageSerializer(instance)
            return Response(serializer.data)
        except LandingPage.DoesNotExist:
            return Response({"detail": "Landing page not found"}, status=404)

