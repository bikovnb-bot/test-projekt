from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, UserLogin

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Профиль"
    fields = ('role', 'phone', 'position')
    extra = 0

class UserLoginInline(admin.TabularInline):
    model = UserLogin
    fields = ('login_time', 'ip_address', 'user_agent')
    readonly_fields = ('login_time', 'ip_address', 'user_agent')
    can_delete = False
    extra = 0
    max_num = 10

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, UserLoginInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role')
    list_filter = ('is_staff', 'is_superuser', 'profile__role')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    list_select_related = ('profile',)

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'
    get_role.short_description = 'Роль'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'user_username')
    list_editable = ('role',)
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user',)

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Имя пользователя'

@admin.register(UserLogin)
class UserLoginAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address', 'short_user_agent')
    list_filter = ('login_time',)
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'login_time', 'ip_address', 'user_agent')

    def short_user_agent(self, obj):
        return obj.user_agent[:50] + '…' if len(obj.user_agent) > 50 else obj.user_agent
    short_user_agent.short_description = 'User-Agent'