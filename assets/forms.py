# assets/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Asset, AssetCategory, AssetAssignment, AssetCheck


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'inventory_number',
            'name', 'category', 'description', 'serial_number',
            'manufacturer', 'model', 'purchase_date', 'cost', 'useful_life_months',
            'location', 'responsible_person', 'status', 'notes'
        ]
        widgets = {
            'inventory_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'useful_life_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_person': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
        labels = {
            'inventory_number': 'Инвентарный номер',
            'name': 'Наименование',
            'category': 'Балансовый счет',
            'description': 'Описание',
            'serial_number': 'Серийный номер',
            'manufacturer': 'Производитель',
            'model': 'Модель',
            'purchase_date': 'Дата ввода в эксплуатацию',
            'cost': 'Балансовая стоимость (₽)',
            'useful_life_months': 'Срок полезного использования, мес.',
            'location': 'Местонахождение',
            'responsible_person': 'Ответственное лицо',
            'status': 'Статус',
            'notes': 'Примечания',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поле инвентарного номера необязательным
        self.fields['inventory_number'].required = False
        self.fields['inventory_number'].help_text = "Оставьте пустым для автоматической генерации"


class AssetAssignmentForm(forms.ModelForm):
    class Meta:
        model = AssetAssignment
        fields = ['assigned_to', 'notes']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
        labels = {
            'assigned_to': 'Закрепить за сотрудником',
            'notes': 'Примечания',
        }


class AssetCheckForm(forms.ModelForm):
    class Meta:
        model = AssetCheck
        fields = ['condition', 'notes']
        widgets = {
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
        labels = {
            'condition': 'Состояние',
            'notes': 'Примечания',
        }