# requests_app/management/commands/migrate_building_to_mixed.py

from django.core.management.base import BaseCommand
from django.db import transaction
from buildings.models import Building, BuildingSection
from requests_app.models import ServiceRequest


class Command(BaseCommand):
    help = 'Переносит заявки со старых зданий на здание "Смешанное здание" с использованием существующих секций'

    def handle(self, *args, **options):
        # 1. Найти целевое здание (правильное имя!)
        try:
            mixed_building = Building.objects.get(name="Смешанное здание")
        except Building.DoesNotExist:
            self.stdout.write(self.style.ERROR('Здание "Смешанное здание" не найдено.'))
            return

        self.stdout.write(f'Найдено здание: {mixed_building.name}')

        # 2. Найти существующие секции у этого здания
        sections = {}
        needed = ['Общежитие', 'Учебный корпус', 'Прилегающая территория']
        for sec_name in needed:
            try:
                section = BuildingSection.objects.get(building=mixed_building, name=sec_name)
                sections[sec_name] = section
                self.stdout.write(f'Найдена секция "{sec_name}"')
            except BuildingSection.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Секция "{sec_name}" не найдена у здания "Смешанное здание".'))
                return

        # 3. Маппинг старых зданий → секции
        mapping = {
            'Студенческое общежитие': sections['Общежитие'],
            'Учебный корпус': sections['Учебный корпус'],
            'Территория': sections['Прилегающая территория'],
        }

        total_updated = 0
        for old_name, new_section in mapping.items():
            try:
                old_building = Building.objects.get(name=old_name)
            except Building.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Здание "{old_name}" не найдено, пропускаем'))
                continue

            qs = ServiceRequest.objects.filter(building=old_building)
            count = qs.count()
            if count == 0:
                self.stdout.write(f'Нет заявок для здания "{old_name}"')
                continue

            self.stdout.write(f'Переношу {count} заявок из "{old_name}" → "{mixed_building.name}" (секция "{new_section.name}")')
            with transaction.atomic():
                updated = qs.update(building=mixed_building, section=new_section)
                total_updated += updated
            self.stdout.write(self.style.SUCCESS(f'Обновлено {updated} заявок'))

        self.stdout.write(self.style.SUCCESS(f'Перенос завершён. Всего обновлено заявок: {total_updated}'))