from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('suggestion/add/', views.add_suggestion, name='add_suggestion'),
    path('bug/add/', views.add_bug, name='add_bug'),
    path('my/suggestions/', views.my_suggestions, name='my_suggestions'),
    path('my/bugs/', views.my_bugs, name='my_bugs'),
    path('admin/suggestions/', views.all_suggestions, name='all_suggestions'),
    path('admin/bugs/', views.all_bugs, name='all_bugs'),
    path('admin/suggestion/<int:pk>/status/', views.change_suggestion_status, name='change_suggestion_status'),
    path('admin/bug/<int:pk>/status/', views.change_bug_status, name='change_bug_status'),
    # Детальный просмотр
    path('suggestion/<int:pk>/', views.suggestion_detail, name='suggestion_detail'),
    path('bug/<int:pk>/', views.bug_detail, name='bug_detail'),
]