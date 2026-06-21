# requests_app/views/permissions.py
from users.models import UserRole


def has_role(user, allowed_roles):
    """
    Проверяет, имеет ли пользователь одну из разрешённых ролей.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    return role and role.role in allowed_roles


def can_view_all_requests(user):
    """Может ли пользователь просматривать все заявки (админ, инженер, диспетчер)."""
    return has_role(user, [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER])


def can_edit_any_request(user):
    """Может ли пользователь редактировать любую заявку (админ, инженер, диспетчер)."""
    return has_role(user, [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER])


def can_delete_request(user):
    """Может ли пользователь удалять заявки (только админ)."""
    return has_role(user, [UserRole.ADMIN])


def can_assign_request(user):
    """Может ли пользователь назначать исполнителей (админ, инженер, диспетчер)."""
    return has_role(user, [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER])


def can_manage_assignees(user):
    """Может ли пользователь управлять дополнительными исполнителями (админ, инженер, диспетчер)."""
    return has_role(user, [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER])


def can_close_request(user, request_obj):
    """
    Может ли пользователь закрыть заявку (админ, инженер, диспетчер, при условии, что заявка выполнена).
    """
    if not can_edit_any_request(user):
        return False
    return request_obj.status == 'completed'


def can_mark_completed(user, request_obj):
    """
    Может ли пользователь отметить заявку как выполненную.
    Проверяет, является ли пользователь исполнителем или имеет роль админ/инженер/диспетчер,
    и что заявка в статусе 'in_progress'.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    if not role:
        return False
    if role.role in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
        return request_obj.status == 'in_progress'
    if role.role == UserRole.WORKER:
        # Проверяем, является ли пользователь основным или дополнительным исполнителем
        is_executor = (request_obj.assigned_to == user or request_obj.assignees.filter(user=user).exists())
        return is_executor and request_obj.status == 'in_progress'
    return False


def can_suspend(user, request_obj):
    """
    Может ли пользователь приостановить заявку.
    Аналогично can_mark_completed.
    """
    return can_mark_completed(user, request_obj)


def can_resume(user, request_obj):
    """
    Может ли пользователь возобновить заявку.
    Только админ, инженер, диспетчер. Заявка должна быть в статусе 'suspended' (или 'closed' для админа).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    if not role:
        return False
    if role.role in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
        if role.role == UserRole.ADMIN:
            return request_obj.status in ['suspended', 'closed']
        return request_obj.status == 'suspended'
    return False


def can_view_request(user, request_obj):
    """
    Может ли пользователь просматривать конкретную заявку.
    Админ/инженер/диспетчер могут всё, рабочий – только свои назначенные, остальные – только созданные.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    if not role:
        return False
    if role.role in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
        return True
    if role.role == UserRole.WORKER:
        return (request_obj.assigned_to == user or request_obj.assignees.filter(user=user).exists())
    # Для VIEWER и других ролей – только созданные
    return request_obj.created_by == user


def can_edit_request(user, request_obj):
    """
    Может ли пользователь редактировать заявку.
    Админ/инженер/диспетчер могут всё, кроме закрытых (только админ может редактировать закрытые).
    Создатель может редактировать, если заявка не закрыта.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'profile', None)
    if not role:
        return False
    if role.role in [UserRole.ADMIN, UserRole.ENGINEER, UserRole.DISPATCHER]:
        if request_obj.status == 'closed' and role.role != UserRole.ADMIN:
            return False
        return True
    # Создатель может редактировать только незакрытые заявки
    if request_obj.created_by == user and request_obj.status != 'closed':
        return True
    return False