from django.utils.translation import gettext_lazy as _

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from sensors.admin import (
    EnvironmentalVariableAdmin,
    FieldSensorAdmin,
    FieldSensorVariableAdmin,
    SensorMeasurementAdmin,
    WeatherMeasurementAdmin,
    WeatherSnapshotAdmin,
    WeatherStationAdmin,
    WeatherStationVariableConfigurationAdmin,
)
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    SensorMeasurement,
    WeatherMeasurement,
    WeatherSnapshot,
    WeatherStation,
    WeatherStationVariableConfiguration,
)


class WagtailEnvironmentalVariableAdmin(SnippetViewSet):
    model = EnvironmentalVariable
    menu_label = _("Environmental variables")
    icon = "list-ul"
    add_to_admin_menu = True
    menu_order = 200
    list_display = EnvironmentalVariableAdmin.list_display
    search_fields = EnvironmentalVariableAdmin.search_fields
    ordering = EnvironmentalVariableAdmin.ordering
    list_filter = EnvironmentalVariableAdmin.list_filter


class WagtailWeatherStationAdmin(SnippetViewSet):
    model = WeatherStation
    menu_label = _("Weather stations")
    icon = "globe"
    list_display = WeatherStationAdmin.list_display
    search_fields = WeatherStationAdmin.search_fields
    ordering = WeatherStationAdmin.ordering
    list_filter = WeatherStationAdmin.list_filter


class WagtailStationVariableAdmin(SnippetViewSet):
    model = WeatherStationVariableConfiguration
    menu_label = _("Station variable mappings")
    icon = "cog"
    list_display = WeatherStationVariableConfigurationAdmin.list_display
    search_fields = WeatherStationVariableConfigurationAdmin.search_fields
    ordering = WeatherStationVariableConfigurationAdmin.ordering
    list_filter = WeatherStationVariableConfigurationAdmin.list_filter


class WagtailFieldSensorAdmin(SnippetViewSet):
    model = FieldSensor
    menu_label = _("Field sensors")
    icon = "cog"
    list_display = FieldSensorAdmin.list_display
    search_fields = FieldSensorAdmin.search_fields
    ordering = FieldSensorAdmin.ordering
    list_filter = FieldSensorAdmin.list_filter


class WagtailFieldSensorVariableAdmin(SnippetViewSet):
    model = FieldSensorVariable
    menu_label = _("Sensor variable mappings")
    icon = "cog"
    list_display = FieldSensorVariableAdmin.list_display
    search_fields = FieldSensorVariableAdmin.search_fields
    ordering = FieldSensorVariableAdmin.ordering
    list_filter = FieldSensorVariableAdmin.list_filter


class WagtailWeatherSnapshotAdmin(SnippetViewSet):
    model = WeatherSnapshot
    menu_label = _("Weather snapshots")
    icon = "doc-full"
    list_display = WeatherSnapshotAdmin.list_display
    search_fields = WeatherSnapshotAdmin.search_fields
    ordering = WeatherSnapshotAdmin.ordering
    list_filter = WeatherSnapshotAdmin.list_filter


class WagtailWeatherMeasurementAdmin(SnippetViewSet):
    model = WeatherMeasurement
    menu_label = _("Weather measurements")
    icon = "table"
    list_display = WeatherMeasurementAdmin.list_display
    search_fields = WeatherMeasurementAdmin.search_fields
    ordering = WeatherMeasurementAdmin.ordering
    list_filter = WeatherMeasurementAdmin.list_filter


class WagtailSensorMeasurementAdmin(SnippetViewSet):
    model = SensorMeasurement
    menu_label = _("Sensor measurements")
    icon = "table"
    list_display = SensorMeasurementAdmin.list_display
    search_fields = SensorMeasurementAdmin.search_fields
    ordering = SensorMeasurementAdmin.ordering
    list_filter = SensorMeasurementAdmin.list_filter


class WagtailWeatherStationGroup(SnippetViewSetGroup):
    menu_label = _("Weather stations")
    menu_icon = "globe"
    menu_order = 201
    items = (
        WagtailWeatherStationAdmin,
        WagtailStationVariableAdmin,
        WagtailWeatherSnapshotAdmin,
        WagtailWeatherMeasurementAdmin,
    )


class WagtailFieldSensorGroup(SnippetViewSetGroup):
    menu_label = _("Field sensors")
    menu_icon = "cog"
    menu_order = 202
    items = (
        WagtailFieldSensorAdmin,
        WagtailFieldSensorVariableAdmin,
        WagtailSensorMeasurementAdmin,
    )


register_snippet(WagtailEnvironmentalVariableAdmin)
register_snippet(WagtailWeatherStationGroup)
register_snippet(WagtailFieldSensorGroup)
