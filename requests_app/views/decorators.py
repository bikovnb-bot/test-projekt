from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .permissions import (
    can_view_all_requests, can_edit_any_request, can_delete_request,
    can_assign_request, can_manage_assignees, can_view_request,
    can_edit_request, can_mark_completed, can_suspend, can_resume,
    can_close_request
)


def permission_required(permission_func, redirect_url=None, message=None):
    """
    Универсальный декоратор для проверки разрешений.
    permission_func – функция, принимающая user и, возможно, request_obj.
    redirect_url – куда перенаправлять при отсутствии прав (если None, то вызывается PermissionDenied).
    message – сообщение об ошибке.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            obj = None
            if 'pk' in kwargs:
                from ..models import ServiceRequest
                try:
                    obj = ServiceRequest.objects.get(pk=kwargs['pk'])
                except ServiceRequest.DoesNotExist:
                    obj = None
            # Проверяем, сколько аргументов принимает функция разрешения
            import inspect
            sig = inspect.signature(permission_func)
            params = sig.parameters
            if obj is not None and len(params) > 1:
                has_perm = permission_func(user, obj)
            else:
                has_perm = permission_func(user)
            if has_perm:
                return view_func(request, *args, **kwargs)
            if redirect_url:
                if message:
                    messages.error(request, message)
                return redirect(redirect_url)
            raise PermissionDenied(message or 'У вас нет прав на это действие.')
        return wrapper
    return decorator


# Конкретные декораторы для удобства
def viewer_required(view_func):
    return permission_required(can_view_all_requests, 'requests_app:request_list', 'У вас нет доступа к списку заявок.')(view_func)


def manager_required(view_func):
    return permission_required(can_edit_any_request, 'requests_app:request_list', 'Требуются права менеджера.')(view_func)


def admin_required(view_func):
    return permission_required(can_delete_request, 'requests_app:request_list', 'Требуются права администратора.')(view_func)


def assign_required(view_func):
    return permission_required(can_assign_request, 'requests_app:request_list', 'У вас нет прав на назначение исполнителей.')(view_func)


def can_view_request_required(view_func):
    return permission_required(can_view_request, 'requests_app:request_list', 'У вас нет доступа к этой заявке.')(view_func)


def can_edit_request_required(view_func):
    return permission_required(can_edit_request, 'requests_app:request_list', 'У вас нет прав на редактирование этой заявки.')(view_func)


def can_mark_completed_required(view_func):
    return permission_required(can_mark_completed, 'requests_app:request_list', 'Вы не можете отметить эту заявку как выполненную.')(view_func)


def can_suspend_required(view_func):
    return permission_required(can_suspend, 'requests_app:request_list', 'Вы не можете приостановить эту заявку.')(view_func)


def can_resume_required(view_func):
    return permission_required(can_resume, 'requests_app:request_list', 'Вы не можете возобновить эту заявку.')(view_func)


def can_close_request_required(view_func):
    return permission_required(can_close_request, 'requests_app:request_list', 'Вы не можете закрыть эту заявку.')(view_func)