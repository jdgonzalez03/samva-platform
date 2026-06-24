from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel

# Create your models here.
class DataTypeChoices(models.TextChoices):
    FLOAT = ("float", _("Float"))
    INTEGER = ("integer", _("Integer"))
    STRING = ("string", _("String"))


class EnvironmentalVariable(models.Model):
    """
    Global definition of a measurable environmental variable.
    Created by the administrator. Shared by stations and field sensors.
    Examples: "Outdoor temperature", "Relative humidity", "Solar radiation".
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Name'),
        help_text=_('Example: Outdoor temperature'),
    )
    unit = models.CharField(
        max_length=20,
        verbose_name=_('Unit'),
        help_text=_('Example: °C, %, mm, W/m²'),
    )
    data_type = models.CharField(
        max_length=10,
        choices=DataTypeChoices.choices,
        default='float',
        verbose_name=_('Data type'),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description'),
    )
 
    panels = [
        MultiFieldPanel([
            FieldPanel('name'),
            FieldPanel('unit'),
            FieldPanel('data_type'),
            FieldPanel('description'),
        ], heading=_('Environment Variable')),
    ]
 
    class Meta:
        verbose_name = _('Environment Variable')
        verbose_name_plural = _('Environment Variables')
        ordering = ['name']
 
    def __str__(self):
        return f'{self.name} ({self.unit})'


class ProviderWeatherStationChoices(models.TextChoices):
    WEATHERLINK = ('weatherlink', 'WeatherLink (Davis)')
    WUNDERGROUND = ('wunderground', 'Weather Wunderground')
    OTHER = ('other', _('Other'))


class WeatherStation(models.Model):
    """
    Physical meteorological station associated with a farm (Farm).
    Covers the entire farm area with its atmospheric sensors.
    Contains the credentials to consume the provider's external API.
    """
    farm = models.ForeignKey(
        'farm.Farm',
        on_delete=models.CASCADE,
        related_name='weather_stations',
        verbose_name=_('Farm'),
        help_text=_('Farm this weather station belongs to'),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
        help_text=_('Example: North field station'),
    )
    provider = models.CharField(
        max_length=30,
        choices=ProviderWeatherStationChoices.choices,
        default='weatherlink',
        verbose_name=_('Provider'),
    )
    station_id = models.CharField(
        max_length=100,
        verbose_name=_('Station ID'),
        help_text=_('Identifier on the provider platform'),
    )
    api_key = models.CharField(
        max_length=255,
        verbose_name=_('API Key'),
    )
    api_secret = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('API Secret'),
        help_text=_('Required by some providers such as WeatherLink v2'),
    )
    polling_interval_minutes = models.PositiveSmallIntegerField(
        default=15,
        verbose_name=_('Polling interval (min)'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Only active stations are polled by Celery'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))
 
    panels = [
        MultiFieldPanel([
            FieldPanel('farm'),
            FieldPanel('name'),
            FieldPanel('is_active'),
        ], heading=_('General information')),
        MultiFieldPanel([
            FieldPanel('provider'),
            FieldPanel('station_id'),
            FieldPanel('api_key'),
            FieldPanel('api_secret'),
            FieldPanel('polling_interval_minutes'),
        ], heading=_('Integration configuration')),
        MultiFieldPanel([
            FieldPanel('created_at', read_only=True),
            FieldPanel('updated_at', read_only=True),
        ], heading=_('Timestamps')),
    ]
 
    class Meta:
        verbose_name = _('Weather station')
        verbose_name_plural = _('Weather stations')
 
    def __str__(self):
        return f'{self.name} — {self.farm.name}'
 


class WeatherStationVariableConfiguration(models.Model):
    """
    Mapping between a WeatherStation and an EnvironmentalVariable.
    field_key is the field name in the provider's API JSON response.

    Example:
        station      → Station UNILLANOS
        env_variable → Outdoor temperature (°C)
        field_key    → "temp_out"
    """

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name='station_variables',
        verbose_name=_('Station'),
    )
    env_variable = models.ForeignKey(
        EnvironmentalVariable,
        on_delete=models.PROTECT,
        related_name='weather_station_variables',
        verbose_name=_('Environmental variable'),
    )
    field_key = models.CharField(
        max_length=100,
        verbose_name=_('Field key'),
        help_text=_('Exact field name in the API response. Example: "temp_out"'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
    )

    panels = [
        FieldPanel('station'),
        FieldPanel('env_variable'),
        FieldPanel('field_key'),
        FieldPanel('is_active'),
    ]

    class Meta:
        verbose_name = _('Station variable')
        verbose_name_plural = _('Station variables')
        unique_together = [
            ('station', 'env_variable'),
            ('station', 'field_key'),
        ]
 
    def __str__(self):
        return f'{self.station.name} - {self.env_variable.name} [{self.field_key}]'



class FieldSensor(models.Model):
    """
    Physical sensor installed in a specific plot.
    Unlike the weather station, the field sensor
    is associated with a concrete plot within the farm.
    A plot can have multiple sensors.
    """

    plot = models.ForeignKey(
        "farm.Plot",
        on_delete=models.CASCADE,
        related_name='field_sensors',
        verbose_name=_('Plot'),
        help_text=_('Plot where the sensor is physically installed'),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
        help_text=_('Example: Soil moisture sensor — North plot'),
    )
    serial_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Serial number'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
    )
    installed_at = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Installation date'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    panels = [
        MultiFieldPanel([
            FieldPanel('plot'),
            FieldPanel('name'),
            FieldPanel('serial_number'),
            FieldPanel('is_active'),
            FieldPanel('installed_at'),
        ], heading=_('Field sensor')),
        MultiFieldPanel([
            FieldPanel('created_at', read_only=True),
            FieldPanel('updated_at', read_only=True),
        ], heading=_('Timestamps')),
    ]

    class Meta:
        verbose_name = _('Field sensor')
        verbose_name_plural = _('Field sensors')
 
    def __str__(self):
        return f'{self.name} ({self.plot.name})'
 
 
class FieldSensorVariable(models.Model):
    """
    Environmental variable measured by a field sensor.
    A sensor can measure more than one variable (temperature + humidity).
    """

    sensor = models.ForeignKey(
        FieldSensor,
        on_delete=models.CASCADE,
        related_name='sensor_variables',
        verbose_name=_('Sensor'),
    )
    env_variable = models.ForeignKey(
        EnvironmentalVariable,
        on_delete=models.PROTECT,
        related_name='field_sensor_variables',
        verbose_name=_('Environmental variable'),
    )

    panels = [
        FieldPanel('sensor'),
        FieldPanel('env_variable'),
    ]

    class Meta:
        verbose_name = _('Sensor variable')
        verbose_name_plural = _('Sensor variables')
        unique_together = [('sensor', 'env_variable')]
 
    def __str__(self):
        return f'{self.sensor.name} - {self.env_variable.name}'


class WeatherSnapshot(models.Model):
    """
    Complete snapshot of a station at a point in time.
    Groups all WeatherMeasurements from the same timestamp.
    Stores the raw JSON for auditing and future re-processing:
    if the admin adds a new WeatherStationVariableConfiguration, the
    raw_json can be re-processed without calling the API again.
    """

    station = models.ForeignKey(
        WeatherStation,
        on_delete=models.CASCADE,
        related_name='snapshots',
        verbose_name=_('Station'),
    )
    recorded_at = models.DateTimeField(
        verbose_name=_('Recorded at'),
        db_index=True,
        help_text=_('Timestamp reported by the station'),
    )
    raw_json = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Raw JSON'),
        help_text=_('Raw API response for auditing and re-processing'),
    )
    ingested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Ingested at'),
        help_text=_('When it was processed by the system'),
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('station'),
            FieldPanel('recorded_at'),
        ], heading=_('Snapshot info')),
        FieldPanel('raw_json'),
        FieldPanel('ingested_at', read_only=True),
    ]

    class Meta:
        verbose_name = _('Weather snapshot')
        verbose_name_plural = _('Weather snapshots')
        unique_together = [('station', 'recorded_at')]
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['station', 'recorded_at']),
        ]

    def __str__(self):
        return f'{self.station.name} — {self.recorded_at:%Y-%m-%d %H:%M}'


class WeatherMeasurement(models.Model):
    """
    Individual value of an environmental variable within a WeatherSnapshot.
    Each snapshot generates as many WeatherMeasurements as
    active WeatherStationVariableConfigurations the station has.
    """

    snapshot = models.ForeignKey(
        'WeatherSnapshot',
        on_delete=models.CASCADE,
        related_name='measurements',
        verbose_name=_('Snapshot'),
    )
    station_variable = models.ForeignKey(
        'WeatherStationVariableConfiguration',
        on_delete=models.PROTECT,
        related_name='measurements',
        verbose_name=_('Station variable'),
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Value'),
        help_text=_('Null if the data was empty or invalid from the source'),
    )

    panels = [
        FieldPanel('snapshot'),
        FieldPanel('station_variable'),
        FieldPanel('value'),
    ]

    class Meta:
        verbose_name = _('Weather measurement')
        verbose_name_plural = _('Weather measurements')
        unique_together = [('snapshot', 'station_variable')]
        indexes = [
            models.Index(fields=['station_variable', 'snapshot']),
        ]

    def __str__(self):
        var = self.station_variable.env_variable
        return f'{var.name}: {self.value} {var.unit}'


class SensorMeasurement(models.Model):
    """
    Record of a value captured by a field sensor.
    Unlike WeatherMeasurement, each reading arrives
    individually from the device (REST endpoint, socket, MQTT, etc.).

    Two differentiated timestamps:
        recorded_at  → when the data occurred according to the sensor
        received_at  → when it arrived at the server

    The difference is important for sensors that accumulate data
    offline and send it in batch when they regain connectivity.
    """

    sensor_variable = models.ForeignKey(
        'FieldSensorVariable',
        on_delete=models.PROTECT,
        related_name='measurements',
        verbose_name=_('Sensor variable'),
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_('Value'),
    )
    recorded_at = models.DateTimeField(
        verbose_name=_('Recorded at'),
        db_index=True,
        help_text=_('Timestamp reported by the sensor'),
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Received at server'),
    )

    panels = [
        FieldPanel('sensor_variable'),
        FieldPanel('value'),
        MultiFieldPanel([
            FieldPanel('recorded_at'),
            FieldPanel('received_at', read_only=True),
        ], heading=_('Timestamps')),
    ]

    class Meta:
        verbose_name = _('Sensor measurement')
        verbose_name_plural = _('Sensor measurements')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['sensor_variable', 'recorded_at']),
        ]

    def __str__(self):
        var = self.sensor_variable.env_variable
        return (
            f'{var.name}: {self.value} {var.unit} '
            f'@ {self.recorded_at:%Y-%m-%d %H:%M}'
        )
 