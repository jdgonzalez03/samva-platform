from django.contrib import admin
from django.utils.translation import gettext as _

from farmer.models import Farmer, Organization

# Register your models here.


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "first_name",
        "last_name",
        "is_active",
        "user__email",
        "organization__name",
    )
    search_fields = ("first_name", "last_name", "user__email")
    list_filter = ("is_active", "created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ("regenerate_api_secret",)

    @admin.action(description=_("Regenerar secreto de API"))
    def regenerate_api_secret(self, request, queryset):
        for farmer in queryset:
            farmer.regenerate_api_secret()
        self.message_user(
            request,
            _("Se regeneró el secreto de API de %d agricultor(es).") % queryset.count(),
        )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    search_fields = ("name",)
    list_filter = ("created_at", "updated_at")
    ordering = ("-created_at",)
