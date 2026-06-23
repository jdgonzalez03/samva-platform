from django.utils.translation import gettext_lazy as _

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from sensors.admin import (
    EnvironmentalVariableAdmin,
    FieldSensorAdmin,
    FieldSensorVariableAdmin,
    WeatherStationAdmin,
    WeatherStationVariableConfigurationAdmin,
)
from sensors.models import (
    EnvironmentalVariable,
    FieldSensor,
    FieldSensorVariable,
    WeatherStation,
    WeatherStationVariableConfiguration,
)


class WagtailEnvironmentalVariableAdmin(SnippetViewSet):
    model = EnvironmentalVariable
    menu_label = _("Environmental variables")
    icon = "list-ul"
    list_display = EnvironmentalVariableAdmin.list_display
    search_fields = EnvironmentalVariableAdmin.search_fields
    ordering = EnvironmentalVariableAdmin.ordering


class WagtailWeatherStationAdmin(SnippetViewSet):
    model = WeatherStation
    menu_label = _("Weather stations")
    icon = "globe"
    list_display = WeatherStationAdmin.list_display
    search_fields = WeatherStationAdmin.search_fields
    ordering = WeatherStationAdmin.ordering


class WagtailStationVariableAdmin(SnippetViewSet):
    model = WeatherStationVariableConfiguration
    menu_label = _("Station variable mappings")
    icon = "cog"
    list_display = WeatherStationVariableConfigurationAdmin.list_display
    search_fields = WeatherStationVariableConfigurationAdmin.search_fields
    ordering = WeatherStationVariableConfigurationAdmin.ordering


class WagtailFieldSensorAdmin(SnippetViewSet):
    model = FieldSensor
    menu_label = _("Field sensors")
    icon = "radio"
    list_display = FieldSensorAdmin.list_display
    search_fields = FieldSensorAdmin.search_fields
    ordering = FieldSensorAdmin.ordering


class WagtailFieldSensorVariableAdmin(SnippetViewSet):
    model = FieldSensorVariable
    menu_label = _("Sensor variable mappings")
    icon = "cog"
    list_display = FieldSensorVariableAdmin.list_display
    search_fields = FieldSensorVariableAdmin.search_fields
    ordering = FieldSensorVariableAdmin.ordering


class WagtailSensorsGroup(SnippetViewSetGroup):
    menu_label = _("Sensors")
    menu_icon = "cogs"
    menu_order = 202
    items = (
        WagtailWeatherStationAdmin,
        WagtailFieldSensorAdmin,
        WagtailEnvironmentalVariableAdmin,
        WagtailStationVariableAdmin,
        WagtailFieldSensorVariableAdmin,
    )


register_snippet(WagtailSensorsGroup)
