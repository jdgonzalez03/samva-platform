from django.urls import path

from farm.api import (
    FarmListAPIView,
    FarmPlotListAPIView,
    FarmWeatherAPIView,
    PlotDetailAPIView,
)

app_name = "farm"

urlpatterns = [
    path('farms/', FarmListAPIView.as_view(), name='farm-list'),
    path(
        'farms/<int:farm_id>/plots/',
        FarmPlotListAPIView.as_view(),
        name='farm-plot-list',
    ),
    path(
        'farms/<int:farm_id>/weather/',
        FarmWeatherAPIView.as_view(),
        name='farm-weather',
    ),
    path(
        'plots/<int:plot_id>/',
        PlotDetailAPIView.as_view(),
        name='plot-detail',
    ),
]
