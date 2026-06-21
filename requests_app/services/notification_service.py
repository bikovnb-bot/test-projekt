# requests_app/services/notification_service.py
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений (Telegram, email)."""

    @staticmethod
    def send_telegram(message):
        """
        Отправляет сообщение в Telegram.
        """
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        if not token or not chat_id:
            logger.warning("Telegram не настроен: отсутствует токен или chat_id")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=5)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Telegram: таймаут при отправке сообщения")
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram: ошибка запроса – {e}")
        except Exception as e:
            logger.exception(f"Telegram: неожиданная ошибка – {e}")

    @staticmethod
    def send_email_new_request(request_obj, admins):
        """
        Отправляет email администраторам о новой публичной заявке.
        """
        if not settings.DEFAULT_FROM_EMAIL or not admins:
            logger.warning("Email не отправлен: не настроен DEFAULT_FROM_EMAIL или список ADMINS")
            return
        try:
            subject = f"New public request #{request_obj.request_number}"
            html_message = render_to_string(
                'requests_app/email_new_public_request.html',
                {'request': request_obj}
            )
            send_mail(
                subject,
                f"Request #{request_obj.request_number} from {request_obj.contact_name or 'Anonymous'}",
                settings.DEFAULT_FROM_EMAIL,
                [email for _, email in admins],
                fail_silently=True,
                html_message=html_message
            )
            logger.info(f"Email отправлен администраторам о заявке #{request_obj.request_number}")
        except Exception as e:
            logger.exception(f"Ошибка при отправке email о заявке #{request_obj.request_number}: {e}")