from django.contrib import admin

from .models import Inspection, InspectionItem


class InspectionItemInline(admin.TabularInline):
    model = InspectionItem
    extra = 0


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'total_detected', 'unidentified', 'created_by', 'applied')
    inlines = [InspectionItemInline]
