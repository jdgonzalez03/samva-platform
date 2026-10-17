from django.shortcuts import render
from django.contrib.auth import authenticate

from drf_spectacular.utils import extend_schema

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated


from .serializers import ApiSecretSerializer, LoginSerializer, MeSerializer
from farmer.models import Farmer
from farmer.serializers import FarmerUpdateSerializer

# Create your views here.
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: None, 401: None})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(request, email=email, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(request=FarmerUpdateSerializer, responses=MeSerializer)
    def patch(self, request):
        farmer = request.user.farmer
        serializer = FarmerUpdateSerializer(
            farmer, 
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(MeSerializer(request.user).data)


class ApiSecretRegenerateView(APIView):
    """Issues a new API secret; every device still sending the old one starts getting 401."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=ApiSecretSerializer)
    def post(self, request):
        farmer = Farmer.objects.filter(user=request.user).first()
        if farmer is None:
            raise NotFound("This account has no farmer profile.")

        farmer.regenerate_api_secret()
        return Response(ApiSecretSerializer(farmer).data)
