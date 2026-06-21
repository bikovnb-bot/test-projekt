# assets/admin.py
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Asset, AssetCategory, AssetAssignment, AssetCheck


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name',)


@admin.register(Asset)
class AssetAdmin(SimpleHistoryAdmin):
    list_display = ('inventory_number', 'name', 'category', 'status', 'responsible_person', 'location')
    list_filter = ('status', 'category')
    search_fields = ('inventory_number', 'name', 'serial_number', 'location')
    autocomplete_fields = ('responsible_person',)
    readonly_fields = ('inventory_number', 'qr_code')
    fieldsets = (
        (None, {'fields': ('inventory_number', 'name', 'category', 'description')}),
        ('Характеристики', {'fields': ('serial_number', 'manufacturer', 'model', 'purchase_date', 'cost')}),
        ('Место и статус', {'fields': ('location', 'responsible_person', 'status')}),
        ('Дополнительно', {'fields': ('qr_code', 'notes')}),
    )


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('asset', 'assigned_to', 'assigned_at', 'returned_at')
    list_filter = ('assigned_at', 'returned_at')
    autocomplete_fields = ('asset', 'assigned_to')


@admin.register(AssetCheck)
class AssetCheckAdmin(admin.ModelAdmin):
    list_display = ('asset', 'checked_by', 'checked_at', 'condition')
    list_filter = ('condition', 'checked_at')