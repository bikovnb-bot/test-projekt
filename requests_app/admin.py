from django.contrib import admin
from .models import ServiceRequest, RequestType, RequestFile, UsedMaterial, Material, RequestHistory, RequestSettings

class RequestFileInline(admin.TabularInline):
    model = RequestFile
    extra = 0
    fields = ('file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

class UsedMaterialInline(admin.TabularInline):
    model = UsedMaterial
    extra = 0
    fields = ('name', 'quantity', 'unit', 'price_per_unit', 'total_price')
    readonly_fields = ('total_price',)

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'building', 'section', 'room_number', 'request_type', 'priority', 'status', 'created_by', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'request_type', 'building', 'section')
    search_fields = ('request_number', 'description', 'building__name', 'room_number')
    autocomplete_fields = ('building', 'section', 'created_by', 'assigned_to')
    readonly_fields = ('request_number', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('request_number', 'building', 'section', 'room_number', 'request_type', 'description')}),
        ('Управление', {'fields': ('priority', 'status', 'assigned_to', 'planned_date', 'completed_date')}),
        ('Дополнительно', {'fields': ('comment', 'created_by', 'created_at', 'updated_at')}),
    )
    inlines = [RequestFileInline, UsedMaterialInline]

@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'default_price', 'quantity_in_stock')
    list_editable = ('quantity_in_stock',)
    search_fields = ('name',)

@admin.register(RequestSettings)
class RequestSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'default_building', 'single_building')
    fields = ('default_building', 'single_building')
    def has_add_permission(self, request):
        return not RequestSettings.objects.exists()