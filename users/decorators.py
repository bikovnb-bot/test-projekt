from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings
from .models import UserRole

# ============================================================
#  ПРЕДИКАТЫ (проверки ролей для использования в других модулях)
# ============================================================

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.ADMIN)
    )

def is_contract_specialist(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.CONTRACT_SPECIALIST)
    )

def is_engineer(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.ENGINEER)
    )

def is_dispatcher(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.DISPATCHER)
    )

def is_worker(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.WORKER)
    )

# ---- Комбинированные проверки для доступа к модулям ----

def has_contract_access(user):
    """Доступ к просмотру договоров."""
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role in [
            UserRole.ADMIN,
            UserRole.CONTRACT_SPECIALIST,
            UserRole.ENGINEER
        ])
    )

def has_contract_edit_access(user):
    """Доступ к редактированию договоров."""
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role in [
            UserRole.ADMIN,
            UserRole.CONTRACT_SPECIALIST
        ])
    )

def has_ticket_full_access(user):
    """Полный доступ к заявкам (создание, назначение, закрытие)."""
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role in [
            UserRole.ADMIN,
            UserRole.ENGINEER,
            UserRole.DISPATCHER
        ])
    )

def has_ticket_assigned_only(user):
    """Доступ только к назначенным заявкам (для рабочего)."""
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == UserRole.WORKER)
    )

# ---- Устаревшие предикаты для обратной совместимости (будут удалены) ----

def is_manager(user):
    """Старое имя – теперь соответствует администратору или специалисту по договорам."""
    return is_admin(user) or is_contract_specialist(user)

def is_viewer(user):
    """Старое имя – теперь любой аутентифицированный пользователь."""
    return user.is_authenticated

def is_contractor(user):
    """Старое имя – теперь соответствует рабочему."""
    return is_worker(user)

# ============================================================
#  ДЕКОРАТОРЫ ДЛЯ ПРЕДСТАВЛЕНИЙ
# ============================================================

def role_required(allowed_roles):
    """
    Универсальный декоратор для проверки, что пользователь имеет одну из разрешённых ролей.
    Суперпользователь имеет доступ всегда.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if hasattr(request.user, 'profile') and request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator

# Конкретные декораторы для отдельных ролей
def admin_required(view_func):
    return role_required([UserRole.ADMIN])(view_func)

def contract_specialist_required(view_func):
    return role_required([UserRole.CONTRACT_SPECIALIST])(view_func)

def engineer_required(view_func):
    return role_required([UserRole.ENGINEER])(view_func)

def dispatcher_required(view_func):
    return role_required([UserRole.DISPATCHER])(view_func)

def worker_required(view_func):
    return role_required([UserRole.WORKER])(view_func)

# Декораторы для доступа к модулям
def contract_access_required(view_func):
    return role_required([UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER])(view_func)

def contract_edit_required(view_func):
    return role_required([UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST])(view_func)

def ticket_full_access_required(view_func):
    return role_required([UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER])(view_func)

def ticket_assigned_only_required(view_func):
    return role_required([UserRole.WORKER])(view_func)

# Устаревшие декораторы для обратной совместимости
def manager_required(view_func):
    return role_required([UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST])(view_func)

def viewer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        return view_func(request, *args, **kwargs)
    return wrapper

def contractor_required(view_func):
    return role_required([UserRole.WORKER])(view_func)