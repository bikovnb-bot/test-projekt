# energy/migrations/000X_migrate_initial_values_to_history.py
from django.db import migrations
from datetime import date

def create_initial_history(apps, schema_editor):
    Meter = apps.get_model('energy', 'Meter')
    InitialValueHistory = apps.get_model('energy', 'InitialValueHistory')
    InitialZoneValueHistory = apps.get_model('energy', 'InitialZoneValueHistory')
    InitialZoneReading = apps.get_model('energy', 'InitialZoneReading')
    Reading = apps.get_model('energy', 'Reading')
    TariffComponent = apps.get_model('energy', 'TariffComponent')

    today = date.today()

    for meter in Meter.objects.all():
        # Определяем дату начала – либо дата первого показания, либо сегодня
        first_reading = Reading.objects.filter(meter=meter).order_by('date').first()
        date_from = first_reading.date if first_reading else today

        if not meter.is_multi_tariff:
            # Однотарифный – создаём запись истории
            # Если уже есть записи в истории, пропускаем (чтобы не дублировать)
            if not InitialValueHistory.objects.filter(meter=meter).exists():
                InitialValueHistory.objects.create(
                    meter=meter,
                    value=meter.initial_value,
                    date_from=date_from
                )
        else:
            # Многотарифный – для каждой зоны
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True
            )
            for comp in components:
                # Проверяем, есть ли уже история для этой зоны
                if InitialZoneValueHistory.objects.filter(meter=meter, tariff_component=comp).exists():
                    continue
                # Пытаемся взять значение из InitialZoneReading
                try:
                    initial = InitialZoneReading.objects.get(meter=meter, tariff_component=comp)
                    value = initial.value
                except InitialZoneReading.DoesNotExist:
                    value = 0
                InitialZoneValueHistory.objects.create(
                    meter=meter,
                    tariff_component=comp,
                    value=value,
                    date_from=date_from
                )

def reverse_migration(apps, schema_editor):
    # Откат – удаляем все записи истории, созданные этой миграцией
    InitialValueHistory = apps.get_model('energy', 'InitialValueHistory')
    InitialZoneValueHistory = apps.get_model('energy', 'InitialZoneValueHistory')
    InitialValueHistory.objects.all().delete()
    InitialZoneValueHistory.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('energy', '0017_alter_initialzonereading_options_and_more'), 
    ]

    operations = [
        migrations.RunPython(create_initial_history, reverse_migration),
    ]
