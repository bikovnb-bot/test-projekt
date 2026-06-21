# assets/management/commands/regenerate_qr_codes.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
from assets.models import Asset


class Command(BaseCommand):
    help = 'Перегенерировать QR-коды для всех объектов Asset'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site-url',
            type=str,
            default=settings.SITE_URL,
            help='Базовый URL сайта (по умолчанию из SITE_URL)'
        )

    def handle(self, *args, **options):
        site_url = options['site_url']
        self.stdout.write(f'Используемый базовый URL: {site_url}')

        assets = Asset.objects.all()
        total = assets.count()
        if total == 0:
            self.stdout.write('Нет объектов для обновления.')
            return

        self.stdout.write(f'Начинаем перегенерацию QR-кодов для {total} объектов...')
        updated = 0

        for asset in assets.iterator():
            # Строим полный URL
            url = f"{site_url}{reverse('assets:asset_detail', args=[asset.pk])}"
            # Генерируем QR-код
            asset.generate_qr_code()
            asset.save(update_fields=['qr_code'])
            updated += 1
            if updated % 50 == 0:
                self.stdout.write(f'Обновлено {updated} из {total}')

        self.stdout.write(self.style.SUCCESS(f'Готово! Обновлено QR-кодов: {updated}'))