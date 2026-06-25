# requests_app/views/public.py
import os
import logging
from datetime import datetime, time

from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone

from buildings.models import Building, BuildingSection
from ..models import RequestSettings, RequestFile, ServiceRequest, RequestType
from ..forms import PublicRequestForm
from ..utils import send_telegram_notification, rate_limit, generate_new_captcha
from ..translator import translate_to_russian

logger = logging.getLogger(__name__)


@csrf_protect
@never_cache
@rate_limit()
def public_request_create(request):
    lang = request.GET.get('lang', 'ru')
    if lang not in ['ru', 'en']:
        lang = 'ru'

    req_settings = RequestSettings.objects.first()
    single_building_mode = req_settings and req_settings.single_building and req_settings.default_building
    default_building = req_settings.default_building if single_building_mode else None

    section_queryset = None
    sections_list = []
    if single_building_mode and default_building:
        if hasattr(default_building, 'sections'):
            section_queryset = default_building.sections.all().order_by('name')
            sections_list = list(section_queryset)
        else:
            section_queryset = default_building.buildingsection_set.all().order_by('name')
            sections_list = list(section_queryset)

    if request.method == 'POST':
        form = PublicRequestForm(request.POST, request.FILES, lang=lang, section_queryset=section_queryset)

        if form.is_valid():
            files = request.FILES.getlist('files')
            max_files = 5
            max_size = 5 * 1024 * 1024
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf']

            # Валидация файлов
            if len(files) > max_files:
                messages.error(request, f'Можно прикрепить не более {max_files} файлов.')
                post_data = request.POST.copy()
                post_data.update(generate_new_captcha(lang))
                form = PublicRequestForm(post_data, request.FILES, lang=lang, section_queryset=section_queryset)
                context = {
                    'form': form,
                    'lang': lang,
                    'hide_navbar': True,
                    'single_building_mode': single_building_mode,
                    'sections_list': sections_list,
                }
                return render(request, f'requests_app/public_request_form_{lang}.html', context)

            for f in files:
                if f.size > max_size:
                    messages.error(request, f'Файл "{f.name}" превышает 5 МБ.')
                    post_data = request.POST.copy()
                    post_data.update(generate_new_captcha(lang))
                    form = PublicRequestForm(post_data, request.FILES, lang=lang, section_queryset=section_queryset)
                    context = {
                        'form': form,
                        'lang': lang,
                        'hide_navbar': True,
                        'single_building_mode': single_building_mode,
                        'sections_list': sections_list,
                    }
                    return render(request, f'requests_app/public_request_form_{lang}.html', context)

                ext = os.path.splitext(f.name)[1].lower()
                if ext not in allowed_extensions:
                    messages.error(request, f'Файл "{f.name}" имеет недопустимое расширение. Разрешены: {", ".join(allowed_extensions)}')
                    post_data = request.POST.copy()
                    post_data.update(generate_new_captcha(lang))
                    form = PublicRequestForm(post_data, request.FILES, lang=lang, section_queryset=section_queryset)
                    context = {
                        'form': form,
                        'lang': lang,
                        'hide_navbar': True,
                        'single_building_mode': single_building_mode,
                        'sections_list': sections_list,
                    }
                    return render(request, f'requests_app/public_request_form_{lang}.html', context)

                # MIME-проверка отключена из-за проблем с python-magic на Windows
                # Проверка расширения и размера достаточна

            # Создание заявки
            sr = form.save(commit=False)
            sr.created_by = None
            sr.assigned_to = None
            sr.status = 'new'
            sr.priority = 'low'
            sr.ip_address = request.META.get('REMOTE_ADDR')

            if single_building_mode:
                sr.building = default_building
                section_id = request.POST.get('section')
                if section_id:
                    try:
                        sr.section = BuildingSection.objects.get(id=section_id)
                    except BuildingSection.DoesNotExist:
                        pass
            else:
                sr.building = form.cleaned_data.get('building')
                sr.section = form.cleaned_data.get('section')

            if lang == 'en' and sr.description:
                sr.description = translate_to_russian(sr.description)

            contact_info = f"Контактное лицо: {sr.contact_name or 'не указано'}, Телефон: {sr.contact_phone or 'не указан'}"
            if sr.comment:
                sr.comment = f"{sr.comment}\n{contact_info}"
            else:
                sr.comment = contact_info

            try:
                sr.save()
                logger.info(f"Создана публичная заявка #{sr.request_number} от {sr.contact_name or 'аноним'}")
            except Exception as e:
                logger.exception(f"Ошибка сохранения публичной заявки: {e}")
                messages.error(request, 'Ошибка при создании заявки. Попробуйте позже.')
                post_data = request.POST.copy()
                post_data.update(generate_new_captcha(lang))
                form = PublicRequestForm(post_data, request.FILES, lang=lang, section_queryset=section_queryset)
                context = {
                    'form': form,
                    'lang': lang,
                    'hide_navbar': True,
                    'single_building_mode': single_building_mode,
                    'sections_list': sections_list,
                }
                return render(request, f'requests_app/public_request_form_{lang}.html', context)

            # Telegram-уведомление
            msg = (
                f"🔔 <b>Новая публичная заявка!</b>\n"
                f"<b>Номер:</b> {sr.request_number}\n"
                f"<b>Здание:</b> {sr.building}\n"
                f"<b>Помещение:</b> {sr.room_number or '—'}\n"
                f"<b>Тип:</b> {sr.request_type.name}\n"
                f"<b>Описание:</b> {sr.description[:100]}\n"
            )
            if sr.contact_name or sr.contact_phone:
                msg += f"<b>Контакты:</b> {sr.contact_name or ''} {sr.contact_phone or ''}\n"
            msg += f"<a href='https://exploitationonline.ru/requests/{sr.id}/'>Перейти к заявке</a>"
            send_telegram_notification(msg)

            # Сохранение файлов
            for f in files:
                try:
                    RequestFile.objects.create(
                        request=sr,
                        file=f,
                        uploaded_by=None,
                        description='Загружено из публичной формы'
                    )
                except Exception as e:
                    logger.exception(f"Ошибка сохранения файла {f.name} для заявки #{sr.request_number}: {e}")

            # Email-уведомление администраторам
            if settings.DEFAULT_FROM_EMAIL and hasattr(settings, 'ADMINS') and settings.ADMINS:
                try:
                    subject = f"New public request #{sr.request_number}"
                    html_message = render_to_string(
                        'requests_app/email_new_public_request.html',
                        {'request': sr}
                    )
                    send_mail(
                        subject,
                        f"Request #{sr.request_number} from {sr.contact_name or 'Anonymous'}",
                        settings.DEFAULT_FROM_EMAIL,
                        [email for _, email in settings.ADMINS],
                        fail_silently=True,
                        html_message=html_message
                    )
                    logger.info(f"Email отправлен администраторам о заявке #{sr.request_number}")
                except Exception as e:
                    logger.exception(f"Ошибка отправки email о публичной заявке #{sr.request_number}: {e}")

            now = timezone.localtime(timezone.now())
            off_hours = False
            if now.weekday() >= 5:
                off_hours = True
            else:
                work_start = time(9, 30)
                work_end = time(18, 0)
                current_time = now.time()
                if current_time < work_start or current_time >= work_end:
                    off_hours = True

            off_param = '&off_hours=1' if off_hours else ''
            return redirect(f'{reverse("requests_app:public_request_success")}?lang={lang}{off_param}')

        else:
            # Ошибки валидации формы
            post_data = request.POST.copy()
            post_data.update(generate_new_captcha(lang))
            form = PublicRequestForm(post_data, request.FILES, lang=lang, section_queryset=section_queryset)
            context = {
                'form': form,
                'lang': lang,
                'hide_navbar': True,
                'single_building_mode': single_building_mode,
                'sections_list': sections_list,
            }
            logger.warning(f"Ошибка валидации публичной формы: {form.errors}")
            return render(request, f'requests_app/public_request_form_{lang}.html', context)

    else:
        form = PublicRequestForm(lang=lang, section_queryset=section_queryset)
        context = {
            'form': form,
            'lang': lang,
            'hide_navbar': True,
            'single_building_mode': single_building_mode,
            'sections_list': sections_list,
        }
        return render(request, f'requests_app/public_request_form_{lang}.html', context)


def public_request_success(request):
    lang = request.GET.get('lang', 'ru')
    if lang not in ['ru', 'en']:
        lang = 'ru'
    off_hours = request.GET.get('off_hours') == '1'
    logger.info(f"Страница успеха публичной заявки, lang={lang}, off_hours={off_hours}")
    return render(request, f'requests_app/public_request_success_{lang}.html', {'hide_navbar': True, 'off_hours': off_hours})