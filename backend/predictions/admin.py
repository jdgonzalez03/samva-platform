from django.contrib import admin

from predictions.models import IrrigationPrediction


@admin.register(IrrigationPrediction)
class IrrigationPredictionAdmin(admin.ModelAdmin):
    list_display = ('plot', 'status', 'irrigation_time_minutes', 'output_label', 'requested_at')
    search_fields = ('plot__name',)
    list_filter = ('status', 'requested_at')
    ordering = ('-requested_at',)
