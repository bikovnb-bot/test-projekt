from django.contrib import admin
from .models import ServiceRequest, RequestType, RequestFile, UsedMaterial, Material, RequestHistory, RequestSettings, MaterialTransaction, RequestNumberSequence


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


class MaterialTransactionInline(admin.TabularInline):
    model = MaterialTransaction
    extra = 0
    fields = ('quantity', 'transaction_type', 'request', 'comment', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False
    show_change_link = False
    max_num = 0  # Не даём добавлять транзакции вручную


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'building', 'section', 'room_number', 'request_type', 'priority', 'status', 'created_by', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'request_type', 'building', 'section', 'created_at')
    search_fields = ('request_number', 'description', 'building__name', 'room_number', 'building__address')
    autocomplete_fields = ('building', 'section', 'created_by', 'assigned_to')
    readonly_fields = ('request_number', 'updated_at')
    fieldsets = (
        (None, {'fields': ('request_number', 'building', 'section', 'room_number', 'request_type', 'description')}),
        ('Управление', {'fields': ('priority', 'status', 'assigned_to', 'planned_date', 'completed_date')}),
        ('Дополнительно', {'fields': ('comment', 'created_by', 'created_at', 'updated_at')}),
    )
    inlines = [RequestFileInline, UsedMaterialInline]
    date_hierarchy = 'created_at'


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'default_price', 'quantity_in_stock', 'min_stock', 'is_low_stock_display')
    list_editable = ('quantity_in_stock', 'min_stock')
    search_fields = ('name',)
    list_filter = ('unit',)
    ordering = ('name',)
    inlines = [MaterialTransactionInline]
    fieldsets = (
        (None, {'fields': ('name', 'unit', 'default_price')}),
        ('Учёт остатков', {'fields': ('quantity_in_stock', 'min_stock')}),
    )

    def is_low_stock_display(self, obj):
        if obj.is_low_stock():
            return '⚠️ Низкий остаток'
        return '✅ Норма'
    is_low_stock_display.short_description = 'Статус остатка'
    is_low_stock_display.boolean = False


@admin.register(MaterialTransaction)
class MaterialTransactionAdmin(admin.ModelAdmin):
    list_display = ('material', 'quantity', 'transaction_type', 'request', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('material__name', 'comment')
    readonly_fields = ('created_at',)
    can_delete = False

    def has_add_permission(self, request):
        return False


@admin.register(RequestSettings)
class RequestSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'default_building', 'single_building')
    fields = ('default_building', 'single_building')

    def has_add_permission(self, request):
        return not RequestSettings.objects.exists()


@admin.register(RequestNumberSequence)
class RequestNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'last_number')
    readonly_fields = ('last_number',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('request', 'user', 'action', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('request__request_number', 'action')
    readonly_fields = ('created_at',)
    can_delete = False

    def has_add_permission(self, request):
        return False