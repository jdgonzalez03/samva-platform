from django.utils.translation import gettext_lazy as _

from farmer.models import Farmer, Organization
from farmer.admin import FarmerAdmin, OrganizationAdmin

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup


class WagtailFarmerSnippetViewSet(SnippetViewSet):
    model = Farmer
    menu_label = _("Granjeros")
    icon = "user"
    list_display = FarmerAdmin.list_display
    search_fields = FarmerAdmin.search_fields
    ordering = FarmerAdmin.ordering


class WagtailOrganizationSnippetViewSet(SnippetViewSet):
    model = Organization
    menu_label = _("Organizaciones")
    icon = "organization"
    list_display = OrganizationAdmin.list_display
    search_fields = OrganizationAdmin.search_fields
    ordering = OrganizationAdmin.ordering


class WagtailFarmerSnippetViewSetGroup(SnippetViewSetGroup):
    menu_label = _("Granjeros")
    menu_icon = "tractor"
    menu_order = 200
    items = (
        WagtailFarmerSnippetViewSet,
        WagtailOrganizationSnippetViewSet,
    )


register_snippet(WagtailFarmerSnippetViewSetGroup)
