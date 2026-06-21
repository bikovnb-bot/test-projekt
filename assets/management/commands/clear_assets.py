# assets/management/commands/clear_assets.py
from django.core.management.base import BaseCommand
from django.db import connection
from assets.models import Asset, AssetCategory, AssetAssignment, AssetCheck


class Command(BaseCommand):
    help = 'Очищает все данные приложения assets (удаляет все записи из моделей Asset, AssetCategory, AssetAssignment, AssetCheck)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Подтверждение без запроса',
        )

    def handle(self, *args, **options):
        if not options.get('yes'):
            confirm = input('Вы уверены, что хотите удалить ВСЕ данные приложения assets? (y/n): ')
            if confirm.lower() != 'y':
                self.stdout.write('Операция отменена.')
                return

        # Сначала удаляем связанные данные (зависимости)
        self.stdout.write('Удаление записей AssetCheck...')
        checks_count, _ = AssetCheck.objects.all().delete()
        self.stdout.write(f'Удалено AssetCheck: {checks_count}')

        self.stdout.write('Удаление записей AssetAssignment...')
        assignments_count, _ = AssetAssignment.objects.all().delete()
        self.stdout.write(f'Удалено AssetAssignment: {assignments_count}')

        self.stdout.write('Удаление записей Asset...')
        assets_count, _ = Asset.objects.all().delete()
        self.stdout.write(f'Удалено Asset: {assets_count}')

        self.stdout.write('Удаление записей AssetCategory...')
        categories_count, _ = AssetCategory.objects.all().delete()
        self.stdout.write(f'Удалено AssetCategory: {categories_count}')

        # Сброс sequence для PostgreSQL (если используется)
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval('assets_asset_id_seq', 1, false);")
                cursor.execute("SELECT setval('assets_assetcategory_id_seq', 1, false);")
                cursor.execute("SELECT setval('assets_assetassignment_id_seq', 1, false);")
                cursor.execute("SELECT setval('assets_assetcheck_id_seq', 1, false);")
                self.stdout.write('Сброс последовательностей (PostgreSQL) выполнен.')

        self.stdout.write(self.style.SUCCESS('Все данные приложения assets успешно удалены!'))