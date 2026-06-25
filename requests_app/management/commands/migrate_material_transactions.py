from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from requests_app.models import UsedMaterial, MaterialTransaction, Material


class Command(BaseCommand):
    help = 'Создаёт MaterialTransaction для всех существующих UsedMaterial записей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, сколько записей будет создано, но не сохранять',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        used_materials = UsedMaterial.objects.select_related('request', 'material').all()
        total = used_materials.count()
        created = 0
        skipped = 0

        self.stdout.write(f'Найдено записей UsedMaterial: {total}')

        if dry_run:
            self.stdout.write('Режим DRY-RUN: транзакции не будут созданы.')
            # Просто покажем пример
            for um in used_materials[:5]:
                self.stdout.write(f'  {um.request.request_number} -> {um.material.name} ({um.quantity} {um.unit})')
            self.stdout.write(f'Всего будет создано {total} транзакций.')
            return

        with db_transaction.atomic():
            for um in used_materials.iterator():
                # Проверяем, существует ли уже транзакция для этой UsedMaterial?
                # Мы не можем связать транзакцию напрямую с UsedMaterial, поэтому проверим по дате, материалу, количеству и заявке
                # Но это неточно. Лучше просто создать новую транзакцию для каждой UsedMaterial.
                # Однако, если скрипт запустить повторно, будут дубли. Поэтому добавим проверку существования.
                # Для простоты создадим транзакцию только если её ещё нет.
                # Проверим наличие транзакции с такими же параметрами (приблизительно)
                existing = MaterialTransaction.objects.filter(
                    material=um.material,
                    request=um.request,
                    quantity=um.quantity,
                    transaction_type='out',
                ).exists()
                if existing:
                    skipped += 1
                    continue

                MaterialTransaction.objects.create(
                    material=um.material,
                    request=um.request,
                    quantity=um.quantity,
                    transaction_type='out',
                    comment=f'Списание при закрытии заявки {um.request.request_number} (миграция)'
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Создано транзакций: {created}, пропущено (уже существуют): {skipped}'))