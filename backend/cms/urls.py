from django.urls import path

from cms.api import LandingPageAPIView


app_name = "cms"

urlpatterns = [
    path('landing/', LandingPageAPIView.as_view(), name='landing'),
]
