# assets/urls.py
from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # ---------- ОСНОВНЫЕ CRUD ----------
    path('', views.AssetListView.as_view(), name='asset_list'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='asset_detail'),
    path('create/', views.AssetCreateView.as_view(), name='asset_create'),
    path('<int:pk>/edit/', views.AssetUpdateView.as_view(), name='asset_edit'),
    path('<int:pk>/delete/', views.AssetDeleteView.as_view(), name='asset_delete'),

    # ---------- ЗАКРЕПЛЕНИЕ И ВОЗВРАТ ----------
    path('<int:pk>/assign/', views.assign_asset, name='assign_asset'),
    path('<int:pk>/return/', views.return_asset, name='return_asset'),

    # ---------- ПРОВЕРКИ И QR ----------
    path('<int:pk>/check/', views.add_asset_check, name='add_check'),
    path('<int:pk>/qr/', views.generate_asset_qr, name='generate_qr'),
    path('<int:pk>/qr/download/', views.download_asset_qr, name='download_qr'),

    # ---------- ФОТО (основное и галерея) ----------
    path('<int:pk>/photo/delete/', views.delete_asset_photo, name='asset_delete_photo'),
    path('<int:pk>/photo/upload/', views.upload_asset_photo, name='asset_upload_photo'),
    path('<int:pk>/gallery/upload/', views.upload_asset_gallery, name='asset_gallery_upload'),
    path('<int:pk>/gallery/delete/<int:photo_id>/', views.delete_asset_photo_gallery, name='asset_gallery_delete'),

    # ---------- ИНВЕНТАРИЗАЦИЯ ----------
    path('<int:pk>/inventory/', views.inventory_asset, name='inventory_asset'),
    path('inventory/', views.inventory_scan, name='inventory_scan'),
    path('inventory/scan-ajax/', views.inventory_scan_ajax, name='inventory_scan_ajax'),
    path('inventory/history/', views.inventory_history, name='inventory_history'),

    # ---------- API ДЛЯ ОФЛАЙН-СИНХРОНИЗАЦИИ ----------
    path('api/assets/', views.asset_list_api, name='api_asset_list'),
    path('api/inventory/sync/', views.inventory_sync_api, name='api_inventory_sync'),

    # ---------- ИМПОРТ / ЭКСПОРТ ----------
    path('import/', views.import_assets_view, name='import_assets'),
    path('export/', views.export_assets, name='export_assets'),

    # ---------- ОТЧЁТЫ ----------
    path('report/', views.asset_report, name='asset_report'),
]