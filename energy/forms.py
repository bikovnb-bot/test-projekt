# energy/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import Meter, Reading, ZoneReading, TariffComponent, ResourceType, MeterDocument, InitialZoneReading
from datetime import date
from decimal import Decimal
from .utils import can_assign_owner


# ------------------------------------------------------------
# ФОРМА ДЛЯ ДОБАВЛЕНИЯ/РЕДАКТИРОВАНИЯ СЧЁТЧИКА
# ------------------------------------------------------------
class MeterForm(forms.ModelForm):
    """
    Форма создания и редактирования прибора учёта.
    Используется в add_meter и MeterUpdateView.
    """
    class Meta:
        model = Meter
        fields = [
            'serial_number', 'resource_type', 'is_multi_tariff',
            'location', 'transformation_ratio', 'initial_value'
        ]
        widgets = {
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'is_multi_tariff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'transformation_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'initial_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
        }
        labels = {
            'serial_number': 'Серийный номер / Название счётчика',
            'resource_type': 'Тип ресурса',
            'is_multi_tariff': 'Многотарифный',
            'location': 'Местоположение',
            'transformation_ratio': 'Коэффициент трансформации',
            'initial_value': 'Начальное показание',
        }
        help_texts = {
            'transformation_ratio': 'Для воды и тепла оставьте 1. Для электроэнергии укажите коэффициент (например, 20).',
            'initial_value': 'Начальное показание счётчика. Для многотарифных – начальные зоны задаются в админке.',
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['resource_type'].queryset = ResourceType.objects.all()

    def save(self, commit=True):
        meter = super().save(commit=False)
        if commit:
            meter.save()
        return meter


# ------------------------------------------------------------
# ФОРМА ДЛЯ ДОБАВЛЕНИЯ ПОКАЗАНИЙ (С ПОДДЕРЖКОЙ ЗОН И ДОКУМЕНТОВ)
# ------------------------------------------------------------
class ReadingForm(forms.Form):
    """
    Форма добавления новых показаний. Поддерживает как однотарифные,
    так и многотарифные счётчики. Динамически подгружает поля для зон.
    Также включает поле для загрузки файла (документа) – фото, скан, PDF.
    """
    meter = forms.ModelChoiceField(
        queryset=Meter.objects.none(),
        label="Счётчик",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control datepicker', 'placeholder': 'дд.мм.гггг'}),
        label="Дата"
    )
    # Поле документа добавляется в __init__

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        from .utils import can_view_all_meters
        if can_view_all_meters(user):
            self.fields['meter'].queryset = Meter.objects.filter(is_active=True)
        else:
            self.fields['meter'].queryset = Meter.objects.filter(is_active=True)

        meter_id = self.data.get('meter') or self.initial.get('meter')
        date_str = self.data.get('date') or self.initial.get('date')

        # Добавляем поле документа для всех случаев
        self.fields['document'] = forms.FileField(
            label='Документ (фото, скан, PDF)',
            required=False,
            widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
            help_text='Максимум 5 МБ. Разрешены JPG, PNG, GIF, BMP, PDF.'
        )

        if meter_id:
            try:
                meter = Meter.objects.get(pk=int(meter_id))
                if meter.is_multi_tariff:
                    from datetime import datetime
                    if date_str:
                        try:
                            target_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                        except ValueError:
                            try:
                                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except ValueError:
                                target_date = date.today()
                    else:
                        target_date = date.today()
                    components = TariffComponent.objects.filter(
                        resource_type=meter.resource_type,
                        is_multi_tariff_zone=True,
                        valid_from__lte=target_date
                    ).exclude(valid_to__lt=target_date)
                    for comp in components:
                        field_name = f'zone_{comp.id}'
                        self.fields[field_name] = forms.DecimalField(
                            label=f"{comp.name} ({comp.unit or meter.resource_type.unit})",
                            max_digits=12, decimal_places=3,
                            widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
                        )
                else:
                    self.fields['value'] = forms.DecimalField(
                        label=f"Показание ({meter.resource_type.unit})",
                        max_digits=12, decimal_places=3,
                        widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
                    )
            except Meter.DoesNotExist:
                pass

    def clean(self):
        """
        Валидация:
            - формат даты,
            - запрет будущей даты,
            - для однотарифных: показание должно быть больше предыдущего или начального,
            - для многотарифных: каждое зональное показание должно быть больше предыдущего или начального.
        """
        cleaned_data = super().clean()
        date_str = cleaned_data.get('date')
        if date_str:
            from datetime import datetime
            try:
                datetime.strptime(date_str, '%d.%m.%Y').date()
            except ValueError:
                try:
                    datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    self.add_error('date', 'Неверный формат даты. Используйте ДД.ММ.ГГГГ или ГГГГ-ММ-ДД.')
                    return cleaned_data

        meter = cleaned_data.get('meter')
        date_val_str = cleaned_data.get('date')
        if not meter or not date_val_str:
            return cleaned_data

        from datetime import datetime
        try:
            date_val = datetime.strptime(date_val_str, '%d.%m.%Y').date()
        except ValueError:
            try:
                date_val = datetime.strptime(date_val_str, '%Y-%m-%d').date()
            except ValueError:
                return cleaned_data

        if date_val > date.today():
            self.add_error('date', 'Дата не может быть в будущем.')

        reset_date = meter.reset_date

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=date_val
            ).exclude(valid_to__lt=date_val)
            for comp in components:
                field_name = f'zone_{comp.id}'
                val = cleaned_data.get(field_name)
                if val is None:
                    self.add_error(field_name, "Обязательное поле")
                    continue

                try:
                    initial = InitialZoneReading.objects.get(meter=meter, tariff_component=comp)
                    base_value = initial.value
                except InitialZoneReading.DoesNotExist:
                    base_value = 0

                prev_qs = ZoneReading.objects.filter(
                    reading__meter=meter,
                    tariff_component=comp,
                    reading__date__lt=date_val
                )
                if reset_date and date_val >= reset_date:
                    prev_qs = prev_qs.filter(reading__date__gte=reset_date)
                prev = prev_qs.order_by('-reading__date').first()

                if prev:
                    if val <= prev.value:
                        self.add_error(field_name, f"Должно быть больше предыдущего ({prev.value})")
                else:
                    if val <= base_value:
                        self.add_error(field_name, f"Должно быть больше начального показания ({base_value})")
        else:
            value = cleaned_data.get('value')
            if value is None:
                self.add_error('value', "Обязательное поле")
            else:
                prev_qs = Reading.objects.filter(meter=meter, date__lt=date_val)
                if reset_date and date_val >= reset_date:
                    prev_qs = prev_qs.filter(date__gte=reset_date)
                prev = prev_qs.order_by('-date').first()

                if prev and prev.value is not None:
                    if value <= prev.value:
                        self.add_error('value', f"Должно быть больше предыдущего ({prev.value})")
                else:
                    if value <= meter.initial_value:
                        self.add_error('value', f"Должно быть больше начального показания ({meter.initial_value})")
        return cleaned_data

    def save(self):
        """
        Сохраняет показание (и зональные, если многотарифный), а также прикреплённый документ.
        """
        meter = self.cleaned_data['meter']
        date_str = self.cleaned_data['date']
        from datetime import datetime
        try:
            date_val = datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            try:
                date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise forms.ValidationError("Неверный формат даты. Используйте ДД.ММ.ГГГГ или ГГГГ-ММ-ДД.")

        reading = Reading(meter=meter, date=date_val)

        if meter.is_multi_tariff:
            reading.save()
            for key, val in self.cleaned_data.items():
                if key.startswith('zone_'):
                    comp_id = int(key.split('_')[1])
                    comp = TariffComponent.objects.get(pk=comp_id)
                    ZoneReading.objects.create(reading=reading, tariff_component=comp, value=val)
            meter.recalc_consumption()
        else:
            reading.value = self.cleaned_data['value']
            reading.save()
            meter.recalc_consumption()

        # Сохраняем документ, если он был загружен
        if self.cleaned_data.get('document'):
            reading.document = self.cleaned_data['document']
            reading.save(update_fields=['document'])

        return reading


# ------------------------------------------------------------
# ФОРМА ДЛЯ РЕДАКТИРОВАНИЯ ПОКАЗАНИЙ (С ЗОНАМИ, ДОКУМЕНТОМ И ВОЗМОЖНОСТЬЮ УДАЛЕНИЯ ФАЙЛА)
# ------------------------------------------------------------
class ReadingEditForm(forms.Form):
    """
    Форма редактирования существующего показания. Позволяет изменить дату,
    значения (для однотарифных) или зональные показания, а также заменить/удалить документ.
    """
    date = forms.DateField(
        input_formats=['%d.%m.%Y', '%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Дата"
    )
    document = forms.FileField(
        label="Заменить документ",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    document_clear = forms.BooleanField(
        label="Удалить текущий документ",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, user, reading, *args, **kwargs):
        self.user = user
        self.reading = reading
        meter = reading.meter
        super().__init__(*args, **kwargs)
        self.initial['date'] = reading.date

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=reading.date
            ).exclude(valid_to__lt=reading.date)
            for comp in components:
                field_name = f'zone_{comp.id}'
                self.fields[field_name] = forms.DecimalField(
                    label=f"{comp.name} ({comp.unit or meter.resource_type.unit})",
                    max_digits=12, decimal_places=3,
                    widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
                )
                zr = reading.zone_readings.filter(tariff_component=comp).first()
                if zr:
                    self.initial[field_name] = zr.value
        else:
            self.fields['value'] = forms.DecimalField(
                label=f"Показание ({meter.resource_type.unit})",
                max_digits=12, decimal_places=3,
                widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
            )
            self.initial['value'] = reading.value

    def clean(self):
        cleaned_data = super().clean()
        reading = self.reading
        meter = reading.meter
        date_val = cleaned_data.get('date')
        if not date_val:
            return cleaned_data

        if date_val > date.today():
            self.add_error('date', 'Дата не может быть в будущем.')

        reset_date = meter.reset_date

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True,
                valid_from__lte=date_val
            ).exclude(valid_to__lt=date_val)
            for comp in components:
                field_name = f'zone_{comp.id}'
                if field_name not in self.fields:
                    continue
                val = cleaned_data.get(field_name)
                if val is None:
                    self.add_error(field_name, "Обязательное поле")
                    continue

                try:
                    initial = InitialZoneReading.objects.get(meter=meter, tariff_component=comp)
                    base_value = initial.value
                except InitialZoneReading.DoesNotExist:
                    base_value = 0

                prev_qs = ZoneReading.objects.filter(
                    reading__meter=meter,
                    tariff_component=comp,
                    reading__date__lt=date_val
                ).exclude(reading__pk=reading.pk)
                if reset_date and date_val >= reset_date:
                    prev_qs = prev_qs.filter(reading__date__gte=reset_date)
                prev = prev_qs.order_by('-reading__date').first()

                if prev:
                    if val <= prev.value:
                        self.add_error(field_name, f"Должно быть больше предыдущего ({prev.value})")
                else:
                    if val <= base_value:
                        self.add_error(field_name, f"Должно быть больше начального показания ({base_value})")
        else:
            value = cleaned_data.get('value')
            if value is None:
                self.add_error('value', "Обязательное поле")
            else:
                prev_qs = Reading.objects.filter(meter=meter, date__lt=date_val).exclude(pk=reading.pk)
                if reset_date and date_val >= reset_date:
                    prev_qs = prev_qs.filter(date__gte=reset_date)
                prev = prev_qs.order_by('-date').first()

                if prev and prev.value is not None:
                    if value <= prev.value:
                        self.add_error('value', f"Должно быть больше предыдущего ({prev.value})")
                else:
                    if value <= meter.initial_value:
                        self.add_error('value', f"Должно быть больше начального показания ({meter.initial_value})")
        return cleaned_data

    def save(self):
        """
        Сохраняет изменения: дату, значения (зональные или обычное),
        а также обновляет документ (замена или удаление).
        """
        reading = self.reading
        reading.date = self.cleaned_data['date']
        meter = reading.meter

        if meter.is_multi_tariff:
            for key, val in self.cleaned_data.items():
                if key.startswith('zone_'):
                    comp_id = int(key.split('_')[1])
                    comp = TariffComponent.objects.get(pk=comp_id)
                    ZoneReading.objects.update_or_create(
                        reading=reading,
                        tariff_component=comp,
                        defaults={'value': val}
                    )
            meter.recalc_consumption()
        else:
            reading.value = self.cleaned_data['value']
            reading.save()
            meter.recalc_consumption()

        # Обработка документа: удаление или замена
        if self.cleaned_data.get('document_clear'):
            if reading.document:
                try:
                    reading.document.delete(save=False)
                except Exception:
                    pass
            reading.document = None
        elif self.cleaned_data.get('document'):
            reading.document = self.cleaned_data['document']
        else:
            # Если файл не передан и чекбокс не отмечен – оставляем как есть
            pass

        reading.save(update_fields=['document'])
        return reading


# ------------------------------------------------------------
# ФОРМА ДЛЯ СБРОСА НАЧАЛЬНЫХ ПОКАЗАНИЙ (ЗАМЕНА ПРИБОРА)
# ------------------------------------------------------------
class ResetInitialReadingsForm(forms.Form):
    """
    Форма для установки новых начальных показаний при замене прибора учёта.
    Позволяет задать дату сброса и новые начальные значения (для однотарифных – одно поле,
    для многотарифных – поля для каждой зоны).
    """
    reset_date = forms.DateField(
        label="Дата сброса (замены прибора)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="С этой даты будут применяться новые начальные показания",
        required=True
    )

    def __init__(self, meter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meter = meter
        self.fields['reset_date'].initial = meter.reset_date or date.today()

        if meter.is_multi_tariff:
            components = TariffComponent.objects.filter(
                resource_type=meter.resource_type,
                is_multi_tariff_zone=True
            ).order_by('name')
            for comp in components:
                try:
                    initial = InitialZoneReading.objects.get(meter=meter, tariff_component=comp)
                    current = initial.value
                except InitialZoneReading.DoesNotExist:
                    current = 0
                self.fields[f'zone_{comp.id}'] = forms.DecimalField(
                    label=f"Начальное показание для зоны «{comp.name}»",
                    initial=current,
                    max_digits=12, decimal_places=3,
                    widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
                )
        else:
            self.fields['initial_value'] = forms.DecimalField(
                label="Новое начальное показание",
                initial=meter.initial_value,
                max_digits=12, decimal_places=3,
                widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'})
            )

    def clean_reset_date(self):
        reset_date = self.cleaned_data['reset_date']
        if reset_date > date.today():
            raise forms.ValidationError("Дата сброса не может быть в будущем.")
        return reset_date


# ------------------------------------------------------------
# ФОРМА ДЛЯ ЗАГРУЗКИ ДОКУМЕНТОВ СЧЁТЧИКА
# ------------------------------------------------------------
class MeterDocumentForm(forms.ModelForm):
    """
    Форма загрузки документов, прикрепляемых к счётчику (паспорт, акт, фото).
    Не путать с документами к показаниям.
    """
    class Meta:
        model = MeterDocument
        fields = ['file', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'file': 'Файл',
            'description': 'Описание (необязательно)',
        }


# ------------------------------------------------------------
# ФОРМА ДЛЯ ИМПОРТА ПОКАЗАНИЙ ИЗ EXCEL
# ------------------------------------------------------------
class ImportReadingsForm(forms.Form):
    """
    Форма импорта показаний из Excel-файла.
    Поддерживает режим проверки (dry run) без сохранения в БД.
    """
    excel_file = forms.FileField(
        label="Excel файл",
        help_text="Файл в формате .xlsx",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    dry_run = forms.BooleanField(
        label="Проверка без сохранения",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )