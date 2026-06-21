# energy/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import (
    ResourceType, TariffComponent, Meter, Reading, ZoneReading,
    InitialZoneReading, MeterDocument, UserLog,
    ArchivedReading, ArchivedZoneReading
)


class InitialZoneReadingInline(admin.TabularInline):
    model = InitialZoneReading
    extra = 1
    fields = ('tariff_component', 'value')
    verbose_name = "Начальное показание по зоне"
    verbose_name_plural = "Начальные показания по зонам"
    classes = ('collapse',)


class ZoneReadingInline(admin.TabularInline):
    model = ZoneReading
    extra = 0
    fields = ('tariff_component', 'value', 'consumption')
    readonly_fields = ('consumption',)
    show_change_link = True
    can_delete = True
    classes = ('collapse',)


class ReadingInline(admin.TabularInline):
    model = Reading
    extra = 0
    fields = ('date', 'value', 'total_consumption_display', 'consumption')
    readonly_fields = ('total_consumption_display', 'consumption')
    show_change_link = True
    can_delete = True
    classes = ('collapse',)

    def total_consumption_display(self, obj):
        return f"{obj.total_consumption():.3f}"
    total_consumption_display.short_description = "Потребление"


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'tariff_components_count')
    search_fields = ('name',)
    list_per_page = 20

    def tariff_components_count(self, obj):
        return obj.tariffcomponent_set.count()
    tariff_components_count.short_description = "Компонентов тарифов"


@admin.register(TariffComponent)
class TariffComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'resource_type', 'price', 'valid_from', 'valid_to', 'is_multi_tariff_zone')
    list_filter = ('resource_type', 'is_multi_tariff_zone', 'valid_from')
    search_fields = ('name',)
    list_editable = ('price',)
    date_hierarchy = 'valid_from'
    fieldsets = (
        (None, {
            'fields': ('resource_type', 'name', 'unit', 'is_multi_tariff_zone')
        }),
        ('Действие', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Цена', {
            'fields': ('price',)
        }),
    )


@admin.register(Meter)
class MeterAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'resource_type', 'is_multi_tariff', 'location', 'is_active', 'last_reading_date', 'last_reading_value')
    list_filter = ('resource_type', 'is_multi_tariff', 'is_active')
    search_fields = ('serial_number', 'location')
    list_editable = ('is_active',)
    list_per_page = 25
    fieldsets = (
        ('Основная информация', {
            'fields': ('serial_number', 'resource_type', 'location')
        }),
        ('Тарифные настройки', {
            'fields': ('is_multi_tariff', 'transformation_ratio')
        }),
        ('Начальные показания', {
            'fields': ('initial_value', 'reset_date'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )
    inlines = [InitialZoneReadingInline, ReadingInline]
    actions = ['archive_selected_readings']

    def last_reading_date(self, obj):
        last = obj.reading_set.order_by('-date').first()
        return last.date if last else '-'
    last_reading_date.short_description = "Последнее показание (дата)"

    def last_reading_value(self, obj):
        last = obj.reading_set.order_by('-date').first()
        if last:
            return f"{last.value} {obj.resource_type.unit}" if not obj.is_multi_tariff else "многотарифный"
        return '-'
    last_reading_value.short_description = "Значение"

    def archive_selected_readings(self, request, queryset):
        self.message_user(request, f"Архивация для {queryset.count()} счётчиков (функция в разработке)")
    archive_selected_readings.short_description = "Архивировать выбранные счётчики"


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('meter_link', 'date', 'value', 'total_consumption', 'anomaly_badge')
    list_filter = ('meter__resource_type', 'date')
    search_fields = ('meter__serial_number',)
    date_hierarchy = 'date'
    list_per_page = 30
    readonly_fields = ('total_consumption',)
    fields = ('meter', 'date', 'value', 'consumption')
    actions = ['recalc_consumption']

    def meter_link(self, obj):
        url = reverse('admin:energy_meter_change', args=[obj.meter.id])
        return format_html('<a href="{}">{}</a>', url, obj.meter.serial_number)
    meter_link.short_description = "Счётчик"

    def total_consumption(self, obj):
        return f"{obj.total_consumption():.3f} {obj.meter.resource_type.unit}"
    total_consumption.short_description = "Потребление"

    def anomaly_badge(self, obj):
        from .utils import get_avg_consumption, is_anomaly
        avg = get_avg_consumption(obj.meter)
        consumption = obj.total_consumption()
        if is_anomaly(consumption, avg):
            return format_html('<span style="color: red; font-weight: bold;">⚠️ Аномалия</span>')
        return '-'
    anomaly_badge.short_description = "Аномалия"

    def recalc_consumption(self, request, queryset):
        for reading in queryset:
            reading.meter.recalc_consumption()
        self.message_user(request, f"Потребление пересчитано для {queryset.count()} показаний")
    recalc_consumption.short_description = "Пересчитать потребление"


@admin.register(ZoneReading)
class ZoneReadingAdmin(admin.ModelAdmin):
    list_display = ('reading_link', 'tariff_component', 'value', 'consumption')
    list_filter = ('tariff_component',)
    search_fields = ('reading__meter__serial_number',)
    readonly_fields = ('consumption',)

    def reading_link(self, obj):
        url = reverse('admin:energy_reading_change', args=[obj.reading.id])
        return format_html('<a href="{}">{}</a>', url, obj.reading)
    reading_link.short_description = "Показание"


@admin.register(MeterDocument)
class MeterDocumentAdmin(admin.ModelAdmin):
    list_display = ('meter_link', 'get_file_name', 'uploaded_at', 'description')
    list_filter = ('meter',)
    search_fields = ('meter__serial_number',)
    readonly_fields = ('uploaded_at',)
    fields = ('meter', 'file', 'description', 'uploaded_at')

    def meter_link(self, obj):
        url = reverse('admin:energy_meter_change', args=[obj.meter.id])
        return format_html('<a href="{}">{}</a>', url, obj.meter.serial_number)
    meter_link.short_description = "Счётчик"

    def get_file_name(self, obj):
        return obj.get_file_name()
    get_file_name.short_description = "Файл"


@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'ip_address')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('user__username', 'model_name', 'object_id', 'details')
    readonly_fields = ('timestamp',)
    fields = ('user', 'action', 'model_name', 'object_id', 'details', 'ip_address', 'timestamp')
    list_per_page = 50


# ------------------------------------------------------------
# АРХИВНЫЕ ПОКАЗАНИЯ (с фильтром по серийному номеру)
# ------------------------------------------------------------

@admin.register(ArchivedReading)
class ArchivedReadingAdmin(admin.ModelAdmin):
    list_display = ('meter_serial', 'date', 'value', 'consumption', 'archived_at')
    list_filter = ('meter_serial', 'archived_at', 'date')
    search_fields = ('meter_serial',)
    list_per_page = 30


@admin.register(ArchivedZoneReading)
class ArchivedZoneReadingAdmin(admin.ModelAdmin):
    list_display = ('archived_reading_link', 'tariff_component', 'value', 'consumption')
    list_filter = ('tariff_component',)
    search_fields = ('archived_reading__meter_serial',)

    def archived_reading_link(self, obj):
        url = reverse('admin:energy_archivedreading_change', args=[obj.archived_reading.id])
        return format_html('<a href="{}">{}</a>', url, obj.archived_reading)
    archived_reading_link.short_description = "Архивное показание"