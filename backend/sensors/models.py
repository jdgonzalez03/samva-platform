from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel

# Create your models here.
class DataTypeChoices(models.TextChoices):
    FLOAT = ("float", _("Float"))
    INTEGER = ("integer", _("Integer"))
    STRING = ("string", _("String"))


class EnvironmentVariable(models.Model):
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