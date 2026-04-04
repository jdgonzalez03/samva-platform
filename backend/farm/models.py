from django.db import models
from django.contrib.gis.db import models as gis_models

from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtailgeowidget.panels import GeoAddressPanel, LeafletPanel
from wagtailgeowidget import geocoders


from farmer.models import Farmer

# Create your models here.
class Farm(models.Model):
    owner = models.ForeignKey(
        Farmer,
        on_delete=models.CASCADE,
        related_name='farms',
        help_text=_('Dueño de la finca'),
        verbose_name=_('Dueño')
    )
    name = models.CharField(
        max_length=100,
        help_text=_('Nombre de la finca'),
        verbose_name=_('Nombre')
    )
    address = models.CharField(
        max_length=255,
        help_text=_('Dirección de la finca'),
        verbose_name=_('Dirección')
    )
    location = gis_models.PointField(
        blank=True,
        null=True,
        help_text=_('Ubicación de la finca'),
        verbose_name=_('Ubicación')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Fecha de creación'),
        verbose_name=_('Fecha de creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_('Fecha de actualización'),
        verbose_name=_('Fecha de actualización')
    )

    panels = [
      MultiFieldPanel([
        FieldPanel('owner'),
        FieldPanel('name'),
      ], heading=_('Información de la finca')),
      MultiFieldPanel([
        GeoAddressPanel('address', geocoder=geocoders.NOMINATIM),
        LeafletPanel('location', address_field='address'),
      ], heading=_('Ubicación')),
      MultiFieldPanel([
        FieldPanel('created_at', read_only=True),
        FieldPanel('updated_at', read_only=True),
      ], heading=_('Metadata')),
    ]

    class Meta:
        verbose_name = _('Finca')
        verbose_name_plural = _('Fincas')
    
    def __str__(self):
        return self.name
    

class Plot(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name='plots',
        help_text=_('Finca a la que pertenece el lote'),
        verbose_name=_('Finca')
    )
    name = models.CharField(
        max_length=100,
        help_text=_('Nombre del lote'),
        verbose_name=_('Nombre')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Descripción del lote'),
        verbose_name=_('Descripción')
    )
    geometry = gis_models.PolygonField(
        blank=True,
        null=True,
        srid=4326,
        help_text=_('Geometría del lote'),
        verbose_name=_('Geometría')
    )
    centroid = gis_models.PointField(
        blank=True,
        null=True,
        help_text=_('Centroide del lote'),
        verbose_name=_('Centroide')
    )
    area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_('Área del lote en hectáreas'),
        verbose_name=_('Área (ha)')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Fecha de creación'),
        verbose_name=_('Fecha de creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_('Fecha de actualización'),
        verbose_name=_('Fecha de actualización')
    )

    panels = [
        MultiFieldPanel([
            FieldPanel('farm'),
            FieldPanel('name'),
            FieldPanel('description'),
        ], heading=_('Información del lote')),
        MultiFieldPanel([
            FieldPanel('geometry'),
        ], heading=_('Geometría del lote')),
        MultiFieldPanel([
            FieldPanel('area_hectares', read_only=True),
            LeafletPanel('centroid', read_only=True),
        ], heading=_('Datos calculados')),
        MultiFieldPanel([
            FieldPanel('created_at', read_only=True),
            FieldPanel('updated_at', read_only=True),
        ], heading=_('Metadata')),
    ]

    class Meta:
        verbose_name = _('Lote')
        verbose_name_plural = _('Lotes')
    
    def __str__(self):
        return f"{self.name} ({self.area_hectares:.2f} ha)" if self.area_hectares else self.name
    
    def save(self, *args, **kwargs):
        if self.geometry:
            self.centroid = self.geometry.centroid
            geom_metric = self.geometry.transform(6933, clone=True)
            area_m2 = geom_metric.area
            self.area_hectares = round(area_m2 / 10000, 2)
        else:
            self.centroid = None
            self.area_hectares = None

        super().save(*args, **kwargs)
