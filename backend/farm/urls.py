from django.urls import path

from farm.api import FarmListAPIView, FarmPlotListAPIView


app_name = "farm"

urlpatterns = [
    path('farms/', FarmListAPIView.as_view(), name='farm-list'),
    path(
        'farms/<int:farm_id>/plots/',
        FarmPlotListAPIView.as_view(),
        name='farm-plot-list',
    ),
]
