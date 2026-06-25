# requests_app/urls.py
# Маршруты приложения для управления заявками, материалами, отчётами и т.д.

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
    bulk_status_update,
)
from .views.materials import (
    material_stock,
    material_add,
    material_edit,
    material_delete,
    material_delete_ajax,
    material_stock_export,
    import_materials,
    download_materials_template,
    material_history,
    material_adjust,
    material_consumption_report,
)
from .views.backup import export_requests_full_backup, import_requests_full_backup
from .views.public import public_request_create, public_request_success
from .views.ajax import api_building_sections, api_overdue_requests, api_captcha

app_name = 'requests_app'

urlpatterns = [
    # ============================================================
    # 1. CRUD для заявок (используются Class-Based Views)
    # ============================================================
    # Список заявок с фильтрацией, поиском и пагинацией
    path('', RequestListView.as_view(), name='request_list'),
    # Детальный просмотр заявки
    path('<int:pk>/', RequestDetailView.as_view(), name='request_detail'),
    # Создание новой заявки
    path('create/', RequestCreateView.as_view(), name='request_create'),
    # Редактирование заявки
    path('<int:pk>/edit/', RequestUpdateView.as_view(), name='request_edit'),
    # Удаление заявки
    path('<int:pk>/delete/', RequestDeleteView.as_view(), name='request_delete'),

    # ============================================================
    # 2. Действия с заявками (изменение статуса, назначение)
    # ============================================================
    # Назначение основного исполнителя
    path('<int:pk>/assign/', request_assign, name='request_assign'),
    # Отметка заявки как выполненной
    path('<int:pk>/complete/', request_mark_completed, name='request_complete'),
    # Приостановка заявки
    path('<int:pk>/suspend/', request_suspend, name='request_suspend'),
    # Возобновление заявки
    path('<int:pk>/resume/', request_resume, name='request_resume'),
    # Закрытие заявки со списанием материалов
    path('<int:pk>/close/', request_close, name='request_close'),

    # ============================================================
    # 3. Отчёты
    # ============================================================
    # Настраиваемый отчёт по заявкам (с выбором колонок и фильтров)
    path('report/custom/', custom_report, name='custom_report'),

    # ============================================================
    # 4. Управление материалами
    # ============================================================
    # Список материалов на складе
    path('materials/', material_stock, name='material_stock'),
    # Добавление нового материала
    path('materials/add/', material_add, name='material_add'),
    # Редактирование материала
    path('materials/<int:pk>/edit/', material_edit, name='material_edit'),
    # Удаление материала (через обычную форму)
    path('materials/<int:pk>/delete/', material_delete, name='material_delete'),
    # AJAX-удаление материала (без перезагрузки страницы)
    path('materials/<int:pk>/delete-ajax/', material_delete_ajax, name='material_delete_ajax'),
    # Экспорт списка материалов в Excel
    path('export/materials/', material_stock_export, name='material_stock_export'),
    # Импорт материалов из Excel
    path('import/materials/', import_materials, name='import_materials'),
    # Скачивание шаблона для импорта
    path('import/materials/template/', download_materials_template, name='download_materials_template'),

    # НОВЫЕ МАРШРУТЫ ДЛЯ РАБОТЫ С МАТЕРИАЛАМИ:
    # История транзакций материала (приход, расход, возврат)
    path('materials/<int:pk>/history/', material_history, name='material_history'),
    # Ручная корректировка остатка материала (приход/списание)
    path('materials/<int:pk>/adjust/', material_adjust, name='material_adjust'),
    # Отчёт по расходу материалов за выбранный период
    path('materials/consumption-report/', material_consumption_report, name='material_consumption_report'),

    # ============================================================
    # 5. Управление дополнительными исполнителями
    # ============================================================
    # Добавление дополнительного исполнителя
    path('assignee/add/<int:pk>/', request_add_assignee, name='request_add_assignee'),
    # Удаление дополнительного исполнителя
    path('assignee/remove/<int:pk>/<int:user_id>/', request_remove_assignee, name='request_remove_assignee'),

    # ============================================================
    # 6. Бэкап и восстановление данных
    # ============================================================
    # Экспорт полного бэкапа заявок (все данные)
    path('backup/export/', export_requests_full_backup, name='export_requests_full_backup'),
    # Импорт/восстановление из бэкапа
    path('backup/import/', import_requests_full_backup, name='import_requests_full_backup'),

    # ============================================================
    # 7. AJAX-эндпоинты для динамической загрузки данных
    # ============================================================
    # Получение списка секций для выбранного здания (при создании/редактировании заявки)
    path('api/building-sections/', api_building_sections, name='api_building_sections'),
    # Получение просроченных заявок для конкретного исполнителя
    path('api/overdue-requests/', api_overdue_requests, name='api_overdue_requests'),
    # Генерация новой капчи для публичной формы
    path('api/captcha/', api_captcha, name='api_captcha'),

    # ============================================================
    # 8. Публичная форма (без авторизации)
    # ============================================================
    # Страница создания публичной заявки (доступна всем)
    path('public/create/', public_request_create, name='public_request_create'),
    # Страница успешного создания публичной заявки
    path('public/success/', public_request_success, name='public_request_success'),

    # ============================================================
    # 9. Массовые операции с заявками
    # ============================================================
    # Массовое изменение статуса выбранных заявок (через чекбоксы в списке)
    path('bulk-status-update/', bulk_status_update, name='bulk_status_update'),
]