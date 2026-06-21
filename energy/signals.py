from datetime import date
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import Reading, ZoneReading, Meter, ArchivedReading, ArchivedZoneReading


@receiver([post_save, post_delete], sender=Reading)
@receiver([post_save, post_delete], sender=ZoneReading)
def recalc_meter_consumption(sender, instance, **kwargs):
    # Если объект помечен как сохраняемый внутри recalc_consumption – пропускаем
    if hasattr(instance, '_skip_recalc') and instance._skip_recalc:
        return
    # Получаем счётчик
    if isinstance(instance, ZoneReading):
        meter = instance.reading.meter
    else:
        meter = instance.meter
    # Если рекурсивный вызов уже идёт – пропускаем
    if hasattr(meter, '_recalc_running') and meter._recalc_running:
        return
    meter.recalc_consumption()


@receiver(pre_delete, sender=Meter)
def archive_meter_readings(sender, instance, **kwargs):
    """
    При удалении счётчика копируем все его показания в архивные таблицы.
    Сохраняем серийный номер счётчика для возможности группировки.
    Если дата показания в будущем – корректируем на сегодняшнюю.
    """
    today = date.today()
    for reading in instance.reading_set.all():
        # Если дата показания в будущем – устанавливаем сегодняшнюю
        if reading.date > today:
            reading.date = today
            reading.save(update_fields=['date'])

        # Создаём архивную запись показания
        arch_reading = ArchivedReading.objects.create(
            meter=instance,
            meter_serial=instance.serial_number,  # сохраняем серийный номер для группировки
            date=reading.date,
            value=reading.value,
            consumption=reading.consumption,
            # archived_at заполнится автоматически
        )
        # Копируем все зональные показания
        for zone_reading in reading.zone_readings.all():
            ArchivedZoneReading.objects.create(
                archived_reading=arch_reading,
                tariff_component=zone_reading.tariff_component,
                value=zone_reading.value,
                consumption=zone_reading.consumption,
            )