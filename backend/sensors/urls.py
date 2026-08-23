from django.urls import path

from sensors.api import (
    SensorHistoryCsvExportAPIView,
    SensorHistoryJsonExportAPIView,
    SensorHistoryPlotAveragesAPIView,
    SensorHistoryReadingsAPIView,
    SensorHistorySeriesAPIView,
    SensorHistoryVariablesAPIView,
)

app_name = "sensors"

urlpatterns = [
    path(
        "farms/<int:farm_id>/history/variables/",
        SensorHistoryVariablesAPIView.as_view(),
        name="history-variables",
    ),
    path(
        "farms/<int:farm_id>/history/readings/",
        SensorHistoryReadingsAPIView.as_view(),
        name="history-readings",
    ),
    path(
        "farms/<int:farm_id>/history/series/",
        SensorHistorySeriesAPIView.as_view(),
        name="history-series",
    ),
    path(
        "farms/<int:farm_id>/history/plot-averages/",
        SensorHistoryPlotAveragesAPIView.as_view(),
        name="history-plot-averages",
    ),
    path(
        "farms/<int:farm_id>/history/export/csv/",
        SensorHistoryCsvExportAPIView.as_view(),
        name="history-export-csv",
    ),
    path(
        "farms/<int:farm_id>/history/export/json/",
        SensorHistoryJsonExportAPIView.as_view(),
        name="history-export-json",
    ),
]
