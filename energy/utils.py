# energy/utils.py

from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum
from .models import Reading, UserLog
from users.decorators import is_admin, has_contract_access, is_contract_specialist, is_engineer

def can_view_all_meters(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role in ['ADMIN', 'CONTRACT_SPECIALIST', 'ENGINEER']

def can_edit_all_meters(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role in ['ADMIN', 'CONTRACT_SPECIALIST', 'ENGINEER']

def can_assign_owner(user):
    if not hasattr(user, 'profile'):
        return False
    return is_admin(user)

def can_view_meter(user, meter):
    return can_view_all_meters(user)

def can_edit_meter(user, meter):
    return can_edit_all_meters(user)

def can_delete_meter(user, meter):
    return is_admin(user)

def can_edit_reading(user, reading):
    return can_edit_meter(user, reading.meter)

def can_delete_reading(user, reading):
    return can_delete_meter(user, reading.meter)

def can_upload_document(user, meter):
    return can_edit_meter(user, meter)

def can_delete_document(user, meter):
    return can_edit_meter(user, meter)


# ------------------------------------------------------------
# Функции для проверки аномального потребления
# ------------------------------------------------------------
def get_avg_consumption(meter, months=6):
    """Возвращает среднемесячное потребление за последние months месяцев (без учёта текущего месяца)"""
    today = date.today()
    start_date = today.replace(day=1) - timedelta(days=1)
    for _ in range(months - 1):
        start_date = start_date.replace(day=1) - timedelta(days=1)
    start_date = start_date.replace(day=1)
    end_date = today.replace(day=1) - timedelta(days=1)
    readings = meter.reading_set.filter(date__gte=start_date, date__lte=end_date)
    if not readings:
        return Decimal('0')
    if meter.is_multi_tariff:
        total = sum(r.total_consumption() for r in readings)
    else:
        total = readings.aggregate(total=Sum('consumption'))['total'] or Decimal('0')
    if total == 0:
        return Decimal('0')
    return total / Decimal(len(readings))

def is_anomaly(consumption, avg_consumption, threshold=2.0):
    if avg_consumption == 0:
        return False
    return consumption > avg_consumption * Decimal(str(threshold))


# ------------------------------------------------------------
# Функции для логирования действий пользователей
# ------------------------------------------------------------
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_action(user, action, model_name='', object_id='', details='', request=None):
    ip_address = get_client_ip(request) if request else None
    UserLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        details=details,
        ip_address=ip_address
    )