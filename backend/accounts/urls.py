from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

app_name = "accounts"

from .views import LoginView, MeView

urlpatterns = [
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
]
