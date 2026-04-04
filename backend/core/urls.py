from rest_framework import routers
from django.urls import path, include

from core.api import GeneralSiteSettingsAPIView, SocialMediaSettingsAPIView

app_name = "core"

api_router = routers.DefaultRouter()

# If you want to register any ViewSets, do it something like this:
# api_router.register("", GeneralSiteSettingsAPIView, basename="general-site-settings")
# api_router.register("", SocialMediaSettingsAPIView, basename="social-media-settings")


api_urls = ([
    path('', include(api_router.urls)),
], app_name)

# But if a View or APIView
urlpatterns = [
    path('general-site-settings/', GeneralSiteSettingsAPIView.as_view(), name='general-site-settings'),
    path('social-media-settings/', SocialMediaSettingsAPIView.as_view(), name='social-media-settings'),
]