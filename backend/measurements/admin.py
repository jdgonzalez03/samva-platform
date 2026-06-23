from django.contrib import admin

from measurements.models import SensorMeasurement, WeatherMeasurement, WeatherSnapshot


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display = ('station', 'recorded_at', 'ingested_at')
    search_fields = ('station__name',)
    list_filter = ('station', 'recorded_at')
    ordering = ('-recorded_at',)


@admin.register(WeatherMeasurement)
class WeatherMeasurementAdmin(admin.ModelAdmin):
    list_display = ('snapshot', 'station_variable', 'value')
    search_fields = ('station_variable__env_variable__name', 'station_variable__station__name')
    list_filter = ('snapshot__station', 'station_variable__env_variable')
    ordering = ('-snapshot__recorded_at',)


@admin.register(SensorMeasurement)
class SensorMeasurementAdmin(admin.ModelAdmin):
    list_display = ('sensor_variable', 'value', 'recorded_at')
    search_fields = ('sensor_variable__sensor__name', 'sensor_variable__env_variable__name')
    list_filter = ('sensor_variable__sensor', 'sensor_variable__env_variable', 'recorded_at')
    ordering = ('-recorded_at',)
