from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel


class PredictionStatus(models.TextChoices):
    PENDING = ('pending', _('Pending'))
    PROCESSING = ('processing', _('Processing'))
    COMPLETED = ('completed', _('Completed'))
    FAILED = ('failed', _('Failed'))


class IrrigationPrediction(models.Model):

    plot = models.ForeignKey(
        'farm.Plot', on_delete=models.CASCADE,
        related_name='irrigation_predictions',
        verbose_name=_('Plot'),
        help_text=_('Farm plot this prediction belongs to'),
    )

    avg_moisture = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_('Average soil moisture'),
        help_text=_('Average soil moisture over the prediction period'),
    )
    avg_temperature = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_('Average temperature'),
        help_text=_('Average air temperature over the prediction period'),
    )
    avg_radiation = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_('Average solar radiation'),
        help_text=_('Average solar radiation over the prediction period'),
    )
    avg_period_hours = models.PositiveSmallIntegerField(
        default=6,
        verbose_name=_('Average period (hours)'),
        help_text=_('Time window in hours for the input averages'),
    )

    irrigation_time_minutes = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name=_('Irrigation time (minutes)'),
        help_text=_('Predicted irrigation duration in minutes'),
    )
    output_label = models.CharField(
        max_length=20, blank=True,
        verbose_name=_('Output label'),
        help_text=_('Fuzzy output label: Nothing / VeryLittle / Little / Long / VeryLong'),
    )

    chart_data = models.JSONField(
        null=True, blank=True,
        verbose_name=_('Chart data'),
        help_text=_('Membership points to render in the frontend'),
    )

    llm_explanation = models.TextField(
        blank=True,
        verbose_name=_('LLM explanation'),
        help_text=_('Natural language explanation of the prediction'),
    )

    status = models.CharField(
        max_length=15, choices=PredictionStatus.choices, default=PredictionStatus.PENDING,
        verbose_name=_('Status'),
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Requested at'),
    )
    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Completed at'),
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('plot'),
            FieldPanel('status'),
        ], heading=_('Irrigation prediction')),
        MultiFieldPanel([
            FieldPanel('avg_moisture'),
            FieldPanel('avg_temperature'),
            FieldPanel('avg_radiation'),
            FieldPanel('avg_period_hours'),
        ], heading=_('Input variables')),
        MultiFieldPanel([
            FieldPanel('irrigation_time_minutes'),
            FieldPanel('output_label'),
        ], heading=_('Output')),
        MultiFieldPanel([
            FieldPanel('chart_data'),
            FieldPanel('llm_explanation'),
        ], heading=_('Details')),
        MultiFieldPanel([
            FieldPanel('requested_at', read_only=True),
            FieldPanel('completed_at', read_only=True),
        ], heading=_('Timestamps')),
    ]

    class Meta:
        verbose_name = _('Irrigation prediction')
        verbose_name_plural = _('Irrigation predictions')
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.plot.name} — {self.status} [{self.requested_at:%Y-%m-%d %H:%M}]'
