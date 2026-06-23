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
# Create your models here.
