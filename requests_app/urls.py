# requests_app/urls.py
from django.urls import path
from .views.requests_cbv import (
    RequestListView,
    RequestDetailView,
    RequestCreateView,
    RequestUpdateView,
    RequestDeleteView,
)
from .views.requests import (
    request_assign,
    request_mark_completed,
    request_suspend,
    request_resume,
    request_close,
    request_add_assignee,
    request_remove_assignee,
    custom_report,
)
from .views.dashboard import get_dashboard_context
from .views.materials import (
    material_stock,
    material_add,
    material_edit,
    material_delete,
    material_delete_ajax,
    material_stock_export,
    import_materials,
    download_materials_template,
)
from .views.backup import export_requests_full_backup, import_requests_full_backup
from .views.public import public_request_create, public_request_success
from .views.ajax import api_building_sections, api_overdue_requests

app_name = 'requests_app'

urlpatterns = [
    # CRUD с использованием CBV
    path('', RequestListView.as_view(), name='request_list'),
    path('<int:pk>/', RequestDetailView.as_view(), name='request_detail'),
    path('create/', RequestCreateView.as_view(), name='request_create'),
    path('<int:pk>/edit/', RequestUpdateView.as_view(), name='request_edit'),
    path('<int:pk>/delete/', RequestDeleteView.as_view(), name='request_delete'),

    # Действия с заявками (FBV)
    path('<int:pk>/assign/', request_assign, name='request_assign'),
    path('<int:pk>/complete/', request_mark_completed, name='request_complete'),
    path('<int:pk>/suspend/', request_suspend, name='request_suspend'),
    path('<int:pk>/resume/', request_resume, name='request_resume'),
    path('<int:pk>/close/', request_close, name='request_close'),

    # Отчёты
    path('report/custom/', custom_report, name='custom_report'),

    # Материалы
    path('materials/', material_stock, name='material_stock'),
    path('materials/add/', material_add, name='material_add'),
    path('materials/<int:pk>/edit/', material_edit, name='material_edit'),
    path('materials/<int:pk>/delete/', material_delete, name='material_delete'),
    path('materials/<int:pk>/delete-ajax/', material_delete_ajax, name='material_delete_ajax'),
    path('export/materials/', material_stock_export, name='material_stock_export'),
    path('import/materials/', import_materials, name='import_materials'),
    path('import/materials/template/', download_materials_template, name='download_materials_template'),

    # Исполнители
    path('assignee/add/<int:pk>/', request_add_assignee, name='request_add_assignee'),
    path('assignee/remove/<int:pk>/<int:user_id>/', request_remove_assignee, name='request_remove_assignee'),

    # Бэкап
    path('backup/export/', export_requests_full_backup, name='export_requests_full_backup'),
    path('backup/import/', import_requests_full_backup, name='import_requests_full_backup'),

    # AJAX
    path('api/building-sections/', api_building_sections, name='api_building_sections'),
    path('api/overdue-requests/', api_overdue_requests, name='api_overdue_requests'),

    # Публичная форма
    path('public/create/', public_request_create, name='public_request_create'),
    path('public/success/', public_request_success, name='public_request_success'),
]