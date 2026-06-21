# requests_app/views/utils.py
import random
import logging
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
import requests

logger = logging.getLogger(__name__)


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        from openpyxl.utils.datetime import from_excel
        try:
            return from_excel(value).date()
        except Exception as e:
            logger.debug(f"Ошибка парсинга Excel даты {value}: {e}")
            pass
    if isinstance(value, str):
        for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def parse_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        from openpyxl.utils.datetime import from_excel
        try:
            return from_excel(value)
        except Exception as e:
            logger.debug(f"Ошибка парсинга Excel datetime {value}: {e}")
            pass
    if isinstance(value, str):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def generate_new_captcha(lang='ru'):
    operators = ['+', '-', '*']
    op = random.choice(operators)
    if op == '+':
        a = random.randint(1, 20)
        b = random.randint(1, 20)
    elif op == '-':
        a = random.randint(5, 20)
        b = random.randint(1, a)
    else:
        a = random.randint(1, 10)
        b = random.randint(1, 10)
    return {
        'captcha_num1': a,
        'captcha_num2': b,
        'captcha_operator': op,
    }


def rate_limit(limit=None, window=None):
    """
    Декоратор ограничения количества запросов с одного IP.
    """
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            _limit = limit if limit is not None else getattr(settings, 'RATE_LIMIT_REQUESTS', 10)
            _window = window if window is not None else getattr(settings, 'RATE_LIMIT_WINDOW', 3600)
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip:
                ip = ip.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            cache_key = f'rate_limit_public_request_{ip}'
            count = cache.get(cache_key, 0)
            if count >= _limit:
                logger.warning(f"Превышен лимит запросов для IP {ip} ({count}/{_limit})")
                return HttpResponseForbidden(
                    "Слишком много заявок. Попробуйте позже. / Too many requests. Please try later."
                )
            cache.set(cache_key, count + 1, _window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def send_telegram_notification(message):
    """Отправляет сообщение в Telegram (обёртка для совместимости)."""
    from ..services import NotificationService
    NotificationService.send_telegram(message)