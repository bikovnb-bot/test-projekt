# energy/models.py

import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


# ------------------------------------------------------------
# ВАЛИДАТОРЫ
# ------------------------------------------------------------

def validate_reading_document(value):
    """
    Валидатор для файлов, прикрепляемых к показаниям счётчиков.
    Разрешены:
        - изображения: .jpg, .jpeg, .png, .gif, .bmp (макс. 5 МБ)
        - PDF-документы: .pdf (макс. 5 МБ)
    """
    if not value:
        return

    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf']
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Разрешены только изображения (JPG, PNG, GIF, BMP) или PDF. '
            f'Загружен файл с расширением {ext}.'
        )

    # Проверка размера файла (не более 5 МБ)
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Размер файла не должен превышать 5 МБ.')


# ------------------------------------------------------------
# МОДЕЛИ
# ------------------------------------------------------------

class ResourceType(models.Model):
    """
    Тип коммунального ресурса: электроэнергия, вода, тепло, газ и т.п.
    Хранит название и единицу измерения.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Тип ресурса")
    unit = models.CharField(max_length=10, verbose_name="Единица измерения")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип ресурса"
        verbose_name_plural = "Типы ресурсов"


class TariffComponent(models.Model):
    """
    Компонент тарифа (например, дневная зона, ночная зона, пиковая зона, базовый тариф).
    Может быть привязан к типу ресурса.
    Поле `is_multi_tariff_zone` = True означает, что этот компонент используется для многотарифных счётчиков.
    """
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.CASCADE,
        verbose_name="Тип ресурса"
    )
    name = models.CharField(
        max_length=50,
        verbose_name="Название компонента"
    )
    unit = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Единица (оставьте пустой, чтобы брать из ресурса)"
    )
    is_multi_tariff_zone = models.BooleanField(
        default=False,
        verbose_name="Является зоной дня/ночи?"
    )
    valid_from = models.DateField(
        verbose_name="Действует с"
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        verbose_name="Действует по"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Цена за единицу"
    )

    def __str__(self):
        unit_display = self.unit or self.resource_type.unit
        return f"{self.resource_type.name} – {self.name}: {self.price} руб/{unit_display}"

    class Meta:
        ordering = ['resource_type', 'name', '-valid_from']
        unique_together = ['resource_type', 'name', 'valid_from']
        verbose_name = "Компонент тарифа"
        verbose_name_plural = "Компоненты тарифов"


class Meter(models.Model):
    """
    Прибор учёта (счётчик). Хранит:
        - серийный номер,
        - тип ресурса,
        - местоположение,
        - активность,
        - коэффициент трансформации (для электроэнергии),
        - флаг многотарифности,
        - начальное показание (для однотарифных),
        - дату сброса (замены прибора) – влияет на пересчёт потребления.
    """
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Серийный номер / Название счётчика"
    )
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.CASCADE,
        verbose_name="Тип ресурса"
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Местоположение"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )
    transformation_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1.0,
        verbose_name="Коэффициент трансформации",
        help_text="Для электроэнергии (трансформаторы). Для воды и тепла оставьте 1."
    )
    is_multi_tariff = models.BooleanField(
        default=False,
        verbose_name="Многотарифный счётчик",
        help_text="Отметьте, если счётчик поддерживает разные тарифы по зонам (день/ночь/пик)"
    )
    initial_value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name="Начальное показание",
        help_text="Для однотарифных счётчиков. Будет вычтено из первого показания."
    )
    reset_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата сброса (замены прибора)",
        help_text="С этой даты потребление считается от новых начальных показаний (для нового прибора)."
    )

    def __str__(self):
        return self.serial_number

    def recalc_consumption(self):
        """
        Пересчитывает потребление для всех показаний данного счётчика.
        Учитывает дату сброса (reset_date) и начальные показания.
        Для многотарифных счётчиков пересчитывает потребление по каждой зоне.
        """
        if hasattr(self, '_recalc_running') and self._recalc_running:
            return
        self._recalc_running = True
        try:
            readings = self.reading_set.order_by('date')
            if not readings:
                return

            def round3(v):
                return v.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

            if self.is_multi_tariff:
                from .models import TariffComponent, InitialZoneReading
                components = TariffComponent.objects.filter(
                    resource_type=self.resource_type,
                    is_multi_tariff_zone=True
                )
                for comp in components:
                    initial = InitialZoneReading.objects.filter(
                        meter=self, tariff_component=comp
                    ).first()
                    base_value = initial.value if initial else Decimal('0')

                    for reading in readings:
                        try:
                            zr = ZoneReading.objects.get(reading=reading, tariff_component=comp)
                        except ZoneReading.DoesNotExist:
                            continue

                        if self.reset_date and reading.date >= self.reset_date:
                            # После даты сброса – ищем предыдущее показание среди записей >= reset_date
                            prev = ZoneReading.objects.filter(
                                reading__meter=self,
                                tariff_component=comp,
                                reading__date__gte=self.reset_date,
                                reading__date__lt=reading.date
                            ).order_by('-reading__date').first()
                            if prev:
                                raw = zr.value - prev.value
                            else:
                                raw = zr.value - base_value
                        else:
                            # Обычная цепочка (без сброса)
                            prev = ZoneReading.objects.filter(
                                reading__meter=self,
                                tariff_component=comp,
                                reading__date__lt=reading.date
                            ).order_by('-reading__date').first()
                            if prev:
                                raw = zr.value - prev.value
                            else:
                                raw = zr.value - base_value

                        new_consumption = round3(raw * self.transformation_ratio)
                        if new_consumption < 0:
                            new_consumption = Decimal('0')
                        if zr.consumption != new_consumption:
                            zr.consumption = new_consumption
                            zr._skip_recalc = True
                            zr.save(update_fields=['consumption'])
                            delattr(zr, '_skip_recalc')
            else:
                # Однотарифный счётчик
                base_value = self.initial_value
                for reading in readings:
                    if reading.value is None:
                        continue

                    if self.reset_date and reading.date >= self.reset_date:
                        prev = Reading.objects.filter(
                            meter=self,
                            date__gte=self.reset_date,
                            date__lt=reading.date
                        ).order_by('-date').first()
                        if prev:
                            raw = reading.value - prev.value
                        else:
                            raw = reading.value - base_value
                    else:
                        prev = Reading.objects.filter(
                            meter=self,
                            date__lt=reading.date
                        ).order_by('-date').first()
                        if prev:
                            raw = reading.value - prev.value
                        else:
                            raw = reading.value - base_value

                    new_consumption = round3(raw * self.transformation_ratio)
                    if new_consumption < 0:
                        new_consumption = Decimal('0')
                    if reading.consumption != new_consumption:
                        reading.consumption = new_consumption
                        reading._skip_recalc = True
                        reading.save(update_fields=['consumption'])
                        delattr(reading, '_skip_recalc')
        finally:
            del self._recalc_running

    class Meta:
        verbose_name = "Счётчик"
        verbose_name_plural = "Счётчики"


class InitialZoneReading(models.Model):
    """
    Начальные показания для каждого компонента (зоны) многотарифного счётчика.
    Используются для расчёта потребления после замены прибора.
    """
    meter = models.OneToOneField(
        Meter,
        on_delete=models.CASCADE,
        related_name='initial_zone_readings'
    )
    tariff_component = models.ForeignKey(TariffComponent, on_delete=models.CASCADE)
    value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        verbose_name="Начальное показание"
    )

    class Meta:
        unique_together = ['meter', 'tariff_component']
        verbose_name = "Начальное показание по зоне"
        verbose_name_plural = "Начальные показания по зонам"

    def __str__(self):
        return f"{self.meter.serial_number} – {self.tariff_component.name}: {self.value}"


class Reading(models.Model):
    """
    Показание прибора учёта. Может быть однотарифным (поле value) или многотарифным
    (связанные записи в ZoneReading).
    Также может содержать прикреплённый документ (фото, скан, PDF) – поле `document`.
    """
    meter = models.ForeignKey(
        Meter,
        on_delete=models.CASCADE,
        verbose_name="Счётчик"
    )
    date = models.DateField(
        verbose_name="Дата показания"
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Показание (суммарное) – для однотарифных счётчиков"
    )
    consumption = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Потребление (рассчитывается автоматически)"
    )
    # ===== НОВОЕ ПОЛЕ ДЛЯ ЗАГРУЗКИ ФАЙЛОВ =====
    document = models.FileField(
        upload_to='reading_documents/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[validate_reading_document],
        verbose_name='Документ (фото, скан, PDF)',
        help_text='Максимум 5 МБ. Разрешены JPG, PNG, GIF, BMP, PDF.'
    )
    # =========================================

    def clean(self):
        if self.date and self.date > timezone.now().date():
            raise ValidationError({'date': 'Дата показания не может быть в будущем.'})

    def save(self, *args, **kwargs):
        if self.consumption is not None:
            self.consumption = self.consumption.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.full_clean()
        super().save(*args, **kwargs)

    def total_consumption(self):
        """Возвращает суммарное потребление (с учётом зон, если счётчик многотарифный)."""
        if self.meter.is_multi_tariff:
            return sum(z.consumption or 0 for z in self.zone_readings.all())
        return self.consumption or 0

    def __str__(self):
        return f"{self.meter.serial_number} – {self.date}"

    class Meta:
        ordering = ['-date']
        unique_together = ['meter', 'date']
        verbose_name = "Показание"
        verbose_name_plural = "Показания"


class ZoneReading(models.Model):
    """
    Показание по конкретной тарифной зоне (компоненту) для многотарифного счётчика.
    """
    reading = models.ForeignKey(
        Reading,
        on_delete=models.CASCADE,
        related_name='zone_readings'
    )
    tariff_component = models.ForeignKey(
        TariffComponent,
        on_delete=models.CASCADE,
        limit_choices_to={'is_multi_tariff_zone': True}
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Показание по зоне"
    )
    consumption = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Потребление по зоне"
    )

    def save(self, *args, **kwargs):
        # При первом сохранении вычисляем потребление, если не задано
        if not self.pk:
            prev = ZoneReading.objects.filter(
                reading__meter=self.reading.meter,
                tariff_component=self.tariff_component,
                reading__date__lt=self.reading.date
            ).order_by('-reading__date').first()
            if prev:
                raw = self.value - prev.value
            else:
                try:
                    initial = InitialZoneReading.objects.get(
                        meter=self.reading.meter,
                        tariff_component=self.tariff_component
                    )
                    raw = self.value - initial.value
                except InitialZoneReading.DoesNotExist:
                    raw = self.value
            rounded = (raw * self.reading.meter.transformation_ratio).quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )
            self.consumption = rounded if rounded > 0 else Decimal('0')
        else:
            if self.consumption is not None:
                self.consumption = self.consumption.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                if self.consumption < 0:
                    self.consumption = Decimal('0')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reading.meter.serial_number} – {self.reading.date} – {self.tariff_component.name}: {self.value}"


class MeterDocument(models.Model):
    """
    Документ, прикреплённый к счётчику (например, паспорт, акт поверки, фото установки).
    Не путать с документами к показаниям.
    """
    meter = models.ForeignKey(
        Meter,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Счётчик"
    )
    file = models.FileField(
        upload_to='meter_documents/%Y/%m/%d/',
        verbose_name="Файл"
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Описание"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата загрузки"
    )

    def __str__(self):
        return f"{self.meter.serial_number} – {self.file.name}"

    def get_file_name(self):
        return self.file.name.split('/')[-1]

    class Meta:
        verbose_name = "Документ счётчика"
        verbose_name_plural = "Документы счётчиков"


class UserLog(models.Model):
    """
    Лог действий пользователей: создание, редактирование, удаление,
    просмотр, импорт, экспорт, вход/выход.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Создание'),
        ('EDIT', 'Редактирование'),
        ('DELETE', 'Удаление'),
        ('VIEW', 'Просмотр'),
        ('IMPORT', 'Импорт'),
        ('EXPORT', 'Экспорт'),
        ('LOGIN', 'Вход'),
        ('LOGOUT', 'Выход'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="Действие"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Модель"
    )
    object_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID объекта"
    )
    details = models.TextField(
        blank=True,
        verbose_name="Детали"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP-адрес"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время"
    )

    class Meta:
        verbose_name = "Лог пользователя"
        verbose_name_plural = "Логи пользователей"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.timestamp}"


# ------------------------------------------------------------
# АРХИВНЫЕ МОДЕЛИ (для хранения удалённых счётчиков)
# ------------------------------------------------------------

class ArchivedReading(models.Model):
    """
    Архивная копия показания при удалении счётчика.
    Сохраняет серийный номер счётчика, показания, потребление и дату архивации.
    """
    meter = models.ForeignKey(
        'Meter',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Счётчик"
    )
    meter_serial = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Серийный номер счётчика"
    )
    date = models.DateField(
        verbose_name="Дата показания"
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Показание (суммарное)"
    )
    consumption = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Потребление"
    )
    archived_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата архивации"
    )

    class Meta:
        ordering = ['-date']
        verbose_name = "Архивное показание"
        verbose_name_plural = "Архивные показания"

    def __str__(self):
        serial = self.meter_serial or (self.meter.serial_number if self.meter else "?")
        return f"{serial} – {self.date} (архив)"


class ArchivedZoneReading(models.Model):
    """
    Архивная копия показания по зоне (для многотарифных счётчиков).
    """
    archived_reading = models.ForeignKey(
        ArchivedReading,
        on_delete=models.CASCADE,
        related_name='zone_readings'
    )
    tariff_component = models.ForeignKey(
        'TariffComponent',
        on_delete=models.SET_NULL,
        null=True
    )
    value = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="Показание по зоне"
    )
    consumption = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Потребление по зоне"
    )

    def __str__(self):
        meter_info = self.archived_reading.meter_serial or (
            self.archived_reading.meter.serial_number if self.archived_reading.meter else "?"
        )
        return f"{meter_info} – {self.archived_reading.date} – {self.tariff_component.name} (архив)"