from django.db.models import Q
from .models import UserRole

def can_edit_contract(user, contract):
    """Проверяет, может ли пользователь редактировать конкретный договор."""
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False

    role = user.profile.role
    if role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST]:
        return True

    # Рабочие (исполнители) могут редактировать только свои договоры?
    # В оригинале было: contractor == user.username или contractor_contact == user.get_full_name()
    # Оставим эту логику, но роль WORKER может редактировать только свои.
    if role == UserRole.WORKER:
        return (contract.contractor == user.username or
                contract.contractor_contact == user.get_full_name())
    return False

def can_view_contract(user, contract):
    """Проверяет, может ли пользователь просматривать договор."""
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False

    role = user.profile.role
    if role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER]:
        return True

    if role == UserRole.WORKER:
        return (contract.contractor == user.username or
                contract.contractor_contact == user.get_full_name())
    return False

def get_visible_contracts(user):
    """Возвращает QuerySet договоров, доступных пользователю."""
    from exploitation_app.models import OperationContract  # локальный импорт

    if not user.is_authenticated:
        return OperationContract.objects.none()

    if user.is_superuser:
        return OperationContract.objects.all()

    if not hasattr(user, 'profile'):
        return OperationContract.objects.none()

    role = user.profile.role
    if role in [UserRole.ADMIN, UserRole.CONTRACT_SPECIALIST, UserRole.ENGINEER]:
        return OperationContract.objects.all()

    if role == UserRole.WORKER:
        return OperationContract.objects.filter(
            Q(contractor=user.username) |
            Q(contractor_contact=user.get_full_name())
        )

    return OperationContract.objects.none()