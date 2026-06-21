# users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    """Встраиваемая форма профиля в страницу пользователя."""
    model = Profile
    can_delete = False
    verbose_name_plural = "Профиль"
    fields = ('role',)
    extra = 0


class CustomUserAdmin(UserAdmin):
    """Расширенная админка для пользователей с отображением роли."""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('is_staff', 'is_superuser', 'profile__role')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_role(self, obj):
        """Возвращает название роли пользователя."""
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Роль'


# Перерегистрируем модель User с кастомным админом
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Админка для модели Profile."""
    list_display = ('user', 'role', 'user_username')
    list_editable = ('role',)
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Имя пользователя'