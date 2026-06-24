from django.contrib import admin

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


@admin.register(EnvironmentalVariable)
class EnvironmentalVariableAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'data_type')
    search_fields = ('name', 'unit')
    list_filter = ('data_type',)
    ordering = ('name',)


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'provider', 'station_id', 'is_active')
    search_fields = ('name', 'farm__name', 'station_id')
    list_filter = ('farm', 'provider', 'is_active')
    ordering = ('-created_at',)


@admin.register(WeatherStationVariableConfiguration)
class WeatherStationVariableConfigurationAdmin(admin.ModelAdmin):
    list_display = ('station', 'env_variable', 'field_key', 'is_active')
    search_fields = ('station__name', 'env_variable__name', 'field_key')
    list_filter = ('station', 'env_variable', 'is_active')
    ordering = ('station', 'env_variable')


@admin.register(FieldSensor)
class FieldSensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'plot', 'serial_number', 'is_active')
    search_fields = ('name', 'plot__name', 'serial_number')
    list_filter = ('plot', 'is_active')
    ordering = ('-created_at',)


@admin.register(FieldSensorVariable)
class FieldSensorVariableAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'env_variable')
    search_fields = ('sensor__name', 'env_variable__name')
    list_filter = ('sensor', 'env_variable')
    ordering = ('sensor', 'env_variable')


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display = ('station', 'recorded_at', 'ingested_at')
    search_fields = ('station__name',)
    list_filter = ('station', 'recorded_at')
    ordering = ('-recorded_at',)


@admin.register(WeatherMeasurement)
class WeatherMeasurementAdmin(admin.ModelAdmin):
    list_display = ('snapshot', 'station_variable', 'value')
    search_fields = (
        'station_variable__env_variable__name',
        'station_variable__station__name',
    )
    list_filter = ('snapshot__station', 'station_variable__env_variable')
    ordering = ('-snapshot__recorded_at',)


@admin.register(SensorMeasurement)
class SensorMeasurementAdmin(admin.ModelAdmin):
    list_display = ('sensor_variable', 'value', 'recorded_at')
    search_fields = (
        'sensor_variable__sensor__name',
        'sensor_variable__env_variable__name',
    )
    list_filter = (
        'sensor_variable__sensor',
        'sensor_variable__env_variable',
        'recorded_at',
    )
    ordering = ('-recorded_at',)

