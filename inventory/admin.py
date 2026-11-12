from django.contrib import admin

from .models import Alert, StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product', 'movement_type', 'quantity', 'created_by')
    list_filter = ('movement_type',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product', 'kind', 'is_resolved')
    list_filter = ('kind', 'is_resolved')
