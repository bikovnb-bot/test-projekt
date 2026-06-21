# buildings/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Building, BuildingSection, BuildingDocument, BuildingOwnershipDocument,
    BuildingArea, BuildingRoom, BuildingSystem, BuildingLandscaping,
    BuildingInspection, BuildingRepair, BuildingTenant, BuildingAppendix
)

# Попытка импорта модели OperationContract из exploitation_app (опционально)
try:
    from exploitation_app.models import OperationContract
    HAS_OPERATION_CONTRACT = True
except ImportError:
    HAS_OPERATION_CONTRACT = False


# ---------- Inlines ----------
class BuildingSectionInline(admin.TabularInline):
    model = BuildingSection
    extra = 1
    fields = ('name', 'order', 'is_common')
    classes = ('collapse',)


class BuildingDocumentInline(admin.TabularInline):
    model = BuildingDocument
    extra = 1
    fields = ('section', 'title', 'file_link', 'uploaded_at')
    readonly_fields = ('file_link', 'uploaded_at')
    classes = ('collapse',)

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file.url)
        return "—"
    file_link.short_description = 'Файл'


class BuildingOwnershipDocumentInline(admin.TabularInline):
    model = BuildingOwnershipDocument
    extra = 1
    fields = ('title', 'file_link', 'uploaded_at')
    readonly_fields = ('file_link', 'uploaded_at')
    classes = ('collapse',)

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file.url)
        return "—"
    file_link.short_description = 'Файл'


class BuildingAreaInline(admin.TabularInline):
    model = BuildingArea
    extra = 1
    fields = ('section', 'area_type', 'name', 'area')
    classes = ('collapse',)


class BuildingRoomInline(admin.TabularInline):
    model = BuildingRoom
    extra = 1
    fields = ('section', 'floor', 'name', 'condition', 'last_repair_year')
    classes = ('collapse',)


class BuildingSystemInline(admin.TabularInline):
    model = BuildingSystem
    extra = 1
    fields = ('section', 'system_type', 'type_desc', 'power', 'last_repair_year')
    classes = ('collapse',)


class BuildingLandscapingInline(admin.TabularInline):
    model = BuildingLandscaping
    extra = 1
    fields = ('section', 'element', 'quantity', 'condition')
    classes = ('collapse',)


class BuildingInspectionInline(admin.TabularInline):
    model = BuildingInspection
    extra = 1
    fields = ('section', 'inspection_date', 'inspector', 'findings')
    classes = ('collapse',)


class BuildingRepairInline(admin.TabularInline):
    model = BuildingRepair
    extra = 1
    fields = ('section', 'object_name', 'repair_type', 'start_date', 'end_date', 'contractor')
    classes = ('collapse',)


class BuildingTenantInline(admin.TabularInline):
    model = BuildingTenant
    extra = 1
    fields = ('section', 'name', 'activity', 'rented_areas')
    classes = ('collapse',)


class BuildingAppendixInline(admin.TabularInline):
    model = BuildingAppendix
    extra = 1
    fields = ('section', 'appendix_type', 'title', 'file_link')
    readonly_fields = ('file_link',)
    classes = ('collapse',)

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Открыть PDF</a>', obj.file.url)
        return "—"
    file_link.short_description = 'Файл'


class OperationContractInline(admin.TabularInline):
    if HAS_OPERATION_CONTRACT:
        model = OperationContract
        fk_name = 'building'
        extra = 0
        fields = ('contract_number', 'contract_type', 'contractor', 'status', 'start_date', 'end_date')
        readonly_fields = ('created_at', 'updated_at')
        show_change_link = True
        classes = ('collapse',)
    else:
        pass


# ---------- Основной админ для Building ----------
@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'cadastral_number', 'total_area', 'year_built', 'building_type', 'is_cultural_heritage')
    list_filter = ('building_type', 'year_built', 'is_cultural_heritage')
    search_fields = ('name', 'address', 'cadastral_number')
    readonly_fields = ('total_area', 'created_at', 'updated_at')
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'cadastral_number', 'address')
        }),
        ('Площади и объёмы', {
            'fields': ('residential_area', 'residential_livable_area', 'non_residential_area', 'total_area',
                       'territory_area', 'building_volume', 'underground_volume')
        }),
        ('Характеристики', {
            'fields': ('number_of_floors', 'year_built', 'number_of_rooms', 'building_type')
        }),
        ('Паспортные данные', {
            'fields': ('balance_cost', 'project_type', 'underground_floors', 'is_cultural_heritage',
                       'emergency_info', 'major_repair_decision', 'demolition_decision')
        }),
        ('Конструктивная характеристика', {
            'fields': ('foundation_desc', 'frame_desc', 'walls_desc', 'floors_desc',
                       'stairs_desc', 'roof_structure_desc', 'roof_cover_desc')
        }),
        ('Контакты', {
            'fields': ('director_name', 'director_phone', 'institution_name')
        }),
        ('Системные поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [
        BuildingSectionInline,
        BuildingDocumentInline,
        BuildingOwnershipDocumentInline,
        BuildingAreaInline,
        BuildingRoomInline,
        BuildingSystemInline,
        BuildingLandscapingInline,
        BuildingInspectionInline,
        BuildingRepairInline,
        BuildingTenantInline,
        BuildingAppendixInline,
    ]
    if HAS_OPERATION_CONTRACT:
        inlines.append(OperationContractInline)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

    def get_list_display(self, request):
        # Можно динамически менять отображение в зависимости от пользователя
        return self.list_display


# ---------- Регистрация остальных моделей с базовыми настройками ----------
@admin.register(BuildingSection)
class BuildingSectionAdmin(admin.ModelAdmin):
    list_display = ('building', 'name', 'order', 'is_common')
    list_filter = ('building', 'is_common')
    search_fields = ('name', 'building__name')
    autocomplete_fields = ('building',)


@admin.register(BuildingDocument)
class BuildingDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'building', 'section', 'uploaded_at')
    list_filter = ('building', 'section')
    search_fields = ('title', 'building__name')
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingOwnershipDocument)
class BuildingOwnershipDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'building', 'uploaded_at')
    list_filter = ('building',)
    search_fields = ('title', 'building__name')
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ('building',)


@admin.register(BuildingArea)
class BuildingAreaAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'area_type', 'name', 'area')
    list_filter = ('area_type', 'building', 'section')
    search_fields = ('name',)
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingRoom)
class BuildingRoomAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'floor', 'name', 'condition')
    list_filter = ('floor', 'condition', 'building', 'section')
    search_fields = ('name',)
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingSystem)
class BuildingSystemAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'system_type', 'type_desc', 'power')
    list_filter = ('system_type', 'building', 'section')
    search_fields = ('building__name',)
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingLandscaping)
class BuildingLandscapingAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'element', 'has_documents', 'condition')
    list_filter = ('has_documents', 'building', 'section')
    search_fields = ('element',)
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingInspection)
class BuildingInspectionAdmin(admin.ModelAdmin):
    list_display = ('building', 'inspection_date', 'inspector', 'findings')
    list_filter = ('inspection_date',)
    search_fields = ('building__name', 'inspector')
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingRepair)
class BuildingRepairAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'object_name', 'repair_type', 'start_date', 'end_date', 'contractor')
    list_filter = ('start_date',)
    search_fields = ('building__name', 'object_name', 'contractor')
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingTenant)
class BuildingTenantAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'name', 'activity', 'lease_term')
    search_fields = ('building__name', 'name')
    autocomplete_fields = ('building', 'section')


@admin.register(BuildingAppendix)
class BuildingAppendixAdmin(admin.ModelAdmin):
    list_display = ('building', 'section', 'appendix_type', 'title', 'uploaded_at')
    list_filter = ('appendix_type',)
    search_fields = ('building__name', 'title')
    readonly_fields = ('uploaded_at',)
    autocomplete_fields = ('building', 'section')