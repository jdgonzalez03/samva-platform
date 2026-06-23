from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel


class WeatherSnapshot(models.Model):
    """
    Complete snapshot of a station at a point in time.
    Groups all WeatherMeasurements from the same timestamp.
    Stores the raw JSON for auditing and future re-processing:
    if the admin adds a new WeatherStationVariableConfiguration, the
    raw_json can be re-processed without calling the API again.
    """

    station = models.ForeignKey(
        "sensors.WeatherStation",
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
        WeatherSnapshot,
        on_delete=models.CASCADE,
        related_name='measurements',
        verbose_name=_('Snapshot'),
    )
    station_variable = models.ForeignKey(
        "sensors.WeatherStationVariableConfiguration",
        on_delete=models.PROTECT,
        related_name='measurements',
        verbose_name=_('Station variable'),
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
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
        "sensors.FieldSensorVariable",
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
