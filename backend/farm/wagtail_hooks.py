from django.utils.translation import gettext_lazy as _

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from farm.models import Farm, Plot
from farm.admin import FarmAdmin, PlotAdmin
from farm.forms import PlotAdminForm



class WagtailFarmAdmin(SnippetViewSet):
    model = Farm
    menu_label = _('Granjas')
    icon = 'folder-open-1'
    list_display = FarmAdmin.list_display
    search_fields = FarmAdmin.search_fields
    ordering = FarmAdmin.ordering


class WagtailPlotAdmin(SnippetViewSet):
    model = Plot
    menu_label = _('Lotes')
    icon = 'folder-open-1'
    list_display = PlotAdmin.list_display
    search_fields = PlotAdmin.search_fields
    ordering = PlotAdmin.ordering

    def get_form_class(self, for_update=False):
        return PlotAdminForm


class WagtailFarmAdminGroup(SnippetViewSetGroup):
    menu_label = _('Granjas')
    menu_icon = 'folder-open-1'
    menu_order = 201
    items = (
        WagtailFarmAdmin,
        WagtailPlotAdmin,
    )


register_snippet(WagtailFarmAdminGroup)

