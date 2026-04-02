from django.contrib import admin

from farmer.models import Farmer, Organization

# Register your models here.

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'is_active', 'user__email', 'organization__name')
    search_fields = ('first_name', 'last_name', 'user__email')
    list_filter = ('is_active', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
