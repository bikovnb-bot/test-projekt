# requests_app/views/__init__.py
from .requests_cbv import (
    RequestListView,
    RequestDetailView,
    RequestCreateView,
    RequestUpdateView,
    RequestDeleteView,
)
from .requests import (
    request_assign,
    request_mark_completed,
    request_suspend,
    request_resume,
    request_close,
    request_add_assignee,
    request_remove_assignee,
    custom_report,
)
from .dashboard import get_dashboard_context
from .materials import (
    material_stock,
    material_add,
    material_edit,
    material_delete,
    material_delete_ajax,
    material_stock_export,
    import_materials,
    download_materials_template,
)
from .backup import export_requests_full_backup, import_requests_full_backup
from .public import public_request_create, public_request_success
from .ajax import api_building_sections, api_overdue_requests