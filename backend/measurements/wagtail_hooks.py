from django.utils.translation import gettext_lazy as _

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from measurements.admin import (
    SensorMeasurementAdmin,
    WeatherMeasurementAdmin,
    WeatherSnapshotAdmin,
)
from measurements.models import (
    SensorMeasurement,
    WeatherMeasurement,
    WeatherSnapshot,
)


class WagtailWeatherSnapshotAdmin(SnippetViewSet):
    model = WeatherSnapshot
    menu_label = _("Weather snapshots")
    icon = "doc-full"
    list_display = WeatherSnapshotAdmin.list_display
    search_fields = WeatherSnapshotAdmin.search_fields
    ordering = WeatherSnapshotAdmin.ordering


class WagtailWeatherMeasurementAdmin(SnippetViewSet):
    model = WeatherMeasurement
    menu_label = _("Weather measurements")
    icon = "table"
    list_display = WeatherMeasurementAdmin.list_display
    search_fields = WeatherMeasurementAdmin.search_fields
    ordering = WeatherMeasurementAdmin.ordering


class WagtailSensorMeasurementAdmin(SnippetViewSet):
    model = SensorMeasurement
    menu_label = _("Sensor measurements")
    icon = "table"
    list_display = SensorMeasurementAdmin.list_display
    search_fields = SensorMeasurementAdmin.search_fields
    ordering = SensorMeasurementAdmin.ordering


class WagtailMeasurementsGroup(SnippetViewSetGroup):
    menu_label = _("Measurements")
    menu_icon = "table"
    menu_order = 203
    items = (
        WagtailWeatherSnapshotAdmin,
        WagtailWeatherMeasurementAdmin,
        WagtailSensorMeasurementAdmin,
    )


register_snippet(WagtailMeasurementsGroup)
