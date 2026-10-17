from django.urls import path

from sensors.api import (
    FieldSensorListAPIView,
    SensorHistoryCsvExportAPIView,
    SensorHistoryJsonExportAPIView,
    SensorHistoryPlotAveragesAPIView,
    SensorHistoryReadingsAPIView,
    SensorHistorySeriesAPIView,
    SensorHistoryVariablesAPIView,
    SensorIngestAPIView,
    WeatherStationCsvExportAPIView,
    WeatherStationDetailAPIView,
    WeatherStationJsonExportAPIView,
    WeatherStationListAPIView,
    WeatherStationReadingsAPIView,
    WeatherStationSeriesAPIView,
)

app_name = "sensors"

urlpatterns = [
    path("ingest/", SensorIngestAPIView.as_view(), name="ingest"),
    path("farms/<int:farm_id>/sensors/", FieldSensorListAPIView.as_view(), name="farm-sensors"),
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
    path(
        "farms/<int:farm_id>/stations/",
        WeatherStationListAPIView.as_view(),
        name="farm-stations",
    ),
    path(
        "stations/<int:station_id>/",
        WeatherStationDetailAPIView.as_view(),
        name="station-detail",
    ),
    path(
        "stations/<int:station_id>/series/",
        WeatherStationSeriesAPIView.as_view(),
        name="station-series",
    ),
    path(
        "stations/<int:station_id>/readings/",
        WeatherStationReadingsAPIView.as_view(),
        name="station-readings",
    ),
    path(
        "stations/<int:station_id>/export/csv/",
        WeatherStationCsvExportAPIView.as_view(),
        name="station-export-csv",
    ),
    path(
        "stations/<int:station_id>/export/json/",
        WeatherStationJsonExportAPIView.as_view(),
        name="station-export-json",
    ),
]
