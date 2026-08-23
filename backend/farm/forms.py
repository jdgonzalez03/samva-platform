from django import forms
from django.contrib.gis import forms as gis_forms
from django.utils.translation import gettext_lazy as _
from leaflet.forms.widgets import LeafletWidget

from farm.models import Farm, Plot

LEAFLET_WIDGET_ATTRS = {
    "map_height": "500px",
    "map_width": "100%",
    "map_srid": 4326,
    "loadevent": "DOMContentLoaded",
}

LEAFLET_READONLY_ATTRS = {
    "map_height": "300px",
    "map_width": "100%",
    "map_srid": 4326,
    "loadevent": "DOMContentLoaded",
    "modifiable": False,
}


class FarmAdminForm(forms.ModelForm):
    boundary = gis_forms.PolygonField(
        widget=LeafletWidget(attrs=LEAFLET_WIDGET_ATTRS),
        required=False,
        label=_("Límite de la finca"),
        help_text=_("Dibuja el polígono que delimita la finca usando las herramientas del mapa."),
    )

    class Meta:
        model = Farm
        fields = "__all__"


class PlotAdminForm(forms.ModelForm):
    geometry = gis_forms.PolygonField(
        widget=LeafletWidget(attrs=LEAFLET_WIDGET_ATTRS),
        required=False,
        label=_("Geometría del lote"),
        help_text=_("Dibuja el polígono del lote usando las herramientas del mapa."),
    )

    centroid = gis_forms.PointField(
        widget=LeafletWidget(attrs=LEAFLET_READONLY_ATTRS),
        required=False,
        label=_("Centroide"),
        help_text=_("Calculado automáticamente al guardar."),
    )

    class Meta:
        model = Plot
        fields = "__all__"
