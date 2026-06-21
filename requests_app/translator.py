# requests_app/translator.py
import hashlib
import logging
import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class YandexTranslateAPI:
    """
    Клиент для Yandex Cloud Translate API.
    """
    def __init__(self):
        self.api_key = settings.YANDEX_CLOUD_API_KEY
        self.folder_id = settings.YANDEX_CLOUD_FOLDER_ID
        self.url = "https://translate.api.cloud.yandex.net/translate/v2/translate"

    def _get_cache_key(self, text, target_lang='ru'):
        """Генерирует уникальный ключ для кэширования."""
        hash_object = hashlib.md5(f"{text}_{target_lang}".encode())
        return f'yandex_translate_{hash_object.hexdigest()}'

    def translate(self, text, target_lang='ru'):
        """
        Переводит текст на указанный язык с кэшированием результата.
        """
        if not text or not text.strip():
            return text

        # Проверяем кэш
        cache_key = self._get_cache_key(text, target_lang)
        cached_text = cache.get(cache_key)
        if cached_text:
            return cached_text

        # Подготавливаем запрос к API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
        }
        body = {
            "targetLanguageCode": target_lang,
            "texts": [text],
        }

        try:
            response = requests.post(self.url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            translated_text = response.json()["translations"][0]["text"]
            cache.set(cache_key, translated_text, timeout=60*60*24*7)
            return translated_text
        except requests.exceptions.Timeout:
            logger.error(f"Yandex Translate: таймаут при переводе текста: {text[:50]}...")
            return text
        except requests.exceptions.RequestException as e:
            logger.error(f"Yandex Translate: ошибка запроса – {e}, текст: {text[:50]}...")
            return text
        except Exception as e:
            logger.exception(f"Yandex Translate: неожиданная ошибка – {e}")
            return text


# Создаём глобальный экземпляр клиента
translator = YandexTranslateAPI()


def translate_to_russian(text):
    """Вспомогательная функция для перевода текста на русский."""
    return translator.translate(text)