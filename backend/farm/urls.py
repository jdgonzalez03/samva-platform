from django.urls import path

from farm.api import (
    FarmListAPIView,
    FarmOverviewAPIView,
    FarmPlotListAPIView,
    PlotDetailAPIView,
    PlotOverviewAPIView,
    PlotSummaryListAPIView,
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
        'farms/<int:farm_id>/overview/',
        FarmOverviewAPIView.as_view(),
        name='farm-overview',
    ),
    path('plots/', PlotSummaryListAPIView.as_view(), name='plot-summary-list'),
    path(
        'plots/<int:plot_id>/',
        PlotDetailAPIView.as_view(),
        name='plot-detail',
    ),
    path(
        'plots/<int:plot_id>/overview/',
        PlotOverviewAPIView.as_view(),
        name='plot-overview',
    ),
]
