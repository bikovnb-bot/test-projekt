# requests_app/migrations/0022_set_initial_request_number_sequence.py
import re
from django.db import migrations


def set_initial_sequence(apps, schema_editor):
    RequestNumberSequence = apps.get_model('requests_app', 'RequestNumberSequence')
    ServiceRequest = apps.get_model('requests_app', 'ServiceRequest')
    
    max_num = 0
    for req in ServiceRequest.objects.all():
        match = re.search(r'(\d+)$', req.request_number)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    if max_num > 0:
        seq, created = RequestNumberSequence.objects.get_or_create(id=1)
        seq.last_number = max_num
        seq.save()
        print(f"Установлен счётчик номеров заявок на {max_num}")
    else:
        # Если заявок нет, оставляем 0
        pass


def reverse_set_sequence(apps, schema_editor):
    # Откат не требуется
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('requests_app', '0021_materialtransaction_requestnumbersequence_and_more'),  # замените на имя предыдущей миграции
    ]

    operations = [
        migrations.RunPython(set_initial_sequence, reverse_set_sequence),
    ]