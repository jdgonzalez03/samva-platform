from django.contrib import admin

from farm.models import Farm, Plot
# Register your models here.

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'address', 'created_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'address')
    ordering = ('-created_at',)


@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = ('name', 'farm', 'created_at')
    list_filter = ('farm', 'created_at')
    search_fields = ('name', 'farm__name')
    ordering = ('-created_at',)
