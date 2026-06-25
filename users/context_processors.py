from .models import UserRole

def user_role(request):
    """Добавляет роль пользователя и флаги в контекст шаблона."""
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        role = request.user.profile.role
        is_super = request.user.is_superuser

        is_admin = is_super or role == UserRole.ADMIN
        is_contract_specialist = is_super or role == UserRole.CONTRACT_SPECIALIST
        is_engineer = is_super or role == UserRole.ENGINEER
        is_dispatcher = is_super or role == UserRole.DISPATCHER
        is_worker = is_super or role == UserRole.WORKER

        return {
            'user_role': role,
            'is_admin': is_admin,
            'is_contract_specialist': is_contract_specialist,
            'is_engineer': is_engineer,
            'is_dispatcher': is_dispatcher,
            'is_worker': is_worker,
            # старые флаги для обратной совместимости (удалить со временем)
            'is_manager': is_admin or is_contract_specialist,
            'is_viewer': request.user.is_authenticated,  # любой аутентифицированный
            'is_contractor': is_worker,
        }
    return {
        'user_role': None,
        'is_admin': False,
        'is_contract_specialist': False,
        'is_engineer': False,
        'is_dispatcher': False,
        'is_worker': False,
        'is_manager': False,
        'is_viewer': False,
        'is_contractor': False,
    }

def user_permissions(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return {
            'user_permissions': request.user.profile.get_all_permissions(),
        }
    return {'user_permissions': set()}