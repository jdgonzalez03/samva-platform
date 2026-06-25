from django.utils.translation import gettext_lazy as _

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from predictions.admin import IrrigationPredictionAdmin
from predictions.models import IrrigationPrediction


class WagtailIrrigationPredictionAdmin(SnippetViewSet):
    model = IrrigationPrediction
    menu_label = _("Irrigation predictions")
    icon = "chart"
    list_display = IrrigationPredictionAdmin.list_display
    search_fields = IrrigationPredictionAdmin.search_fields
    ordering = IrrigationPredictionAdmin.ordering
    list_filter = IrrigationPredictionAdmin.list_filter


class WagtailFuzzyLogicGroup(SnippetViewSetGroup):
    menu_label = _("Fuzzy Logic")
    menu_icon = "success"
    menu_order = 203
    items = (WagtailIrrigationPredictionAdmin,)


register_snippet(WagtailFuzzyLogicGroup)
