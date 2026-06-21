# buildings/urls.py

from django.urls import path
from . import views

app_name = 'buildings'

urlpatterns = [
    path('<int:pk>/passport/', views.passport_detail, name='passport_detail'),
    path('<int:pk>/passport/edit/', views.passport_edit, name='passport_edit'),
    path('<int:pk>/passport/export/', views.passport_export_excel, name='passport_export'),
    path('<int:pk>/file/<str:file_type>/<int:file_id>/delete/', views.delete_building_file, name='delete_file'),
    path('', views.building_list, name='building_list'),
]