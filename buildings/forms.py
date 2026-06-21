# buildings/forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import (
    Building, BuildingArea, BuildingRoom, BuildingSystem,
    BuildingLandscaping, BuildingInspection, BuildingRepair,
    BuildingTenant, BuildingAppendix, BuildingDocument,
    BuildingOwnershipDocument, BuildingSection
)


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cadastral_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'residential_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'residential_livable_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'non_residential_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_area': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'number_of_floors': forms.NumberInput(attrs={'class': 'form-control'}),
            'year_built': forms.NumberInput(attrs={'class': 'form-control'}),
            'number_of_rooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'building_type': forms.Select(attrs={'class': 'form-select'}),
            'balance_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'territory_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'project_type': forms.TextInput(attrs={'class': 'form-control'}),
            'underground_floors': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_cultural_heritage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'emergency_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'major_repair_decision': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'demolition_decision': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'building_volume': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'underground_volume': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'foundation_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'frame_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'walls_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'floors_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'stairs_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'roof_structure_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'roof_cover_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'director_name': forms.TextInput(attrs={'class': 'form-control'}),
            'director_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


# Inline formsets

BuildingAreaFormSet = inlineformset_factory(
    Building, BuildingArea,
    fields=['area_type', 'name', 'area'],   # section удалён (не используется в новой вкладке)
    extra=1, can_delete=True,
    widgets={
        'area_type': forms.Select(attrs={'class': 'form-select'}),
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    }
)

BuildingRoomFormSet = inlineformset_factory(
    Building, BuildingRoom,
    fields=['section', 'floor', 'name', 'ceiling_finish', 'walls_finish', 'floors_finish',
            'windows', 'doors', 'last_repair_type', 'last_repair_year', 'condition', 'recommendations'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'floor': forms.Select(attrs={'class': 'form-select'}),
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'ceiling_finish': forms.TextInput(attrs={'class': 'form-control'}),
        'walls_finish': forms.TextInput(attrs={'class': 'form-control'}),
        'floors_finish': forms.TextInput(attrs={'class': 'form-control'}),
        'windows': forms.TextInput(attrs={'class': 'form-control'}),
        'doors': forms.TextInput(attrs={'class': 'form-control'}),
        'last_repair_type': forms.TextInput(attrs={'class': 'form-control'}),
        'last_repair_year': forms.NumberInput(attrs={'class': 'form-control'}),
        'condition': forms.TextInput(attrs={'class': 'form-control'}),
        'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    }
)

BuildingSystemFormSet = inlineformset_factory(
    Building, BuildingSystem,
    fields='__all__', exclude=['building'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'system_type': forms.Select(attrs={'class': 'form-select'}),
        'system_type_other': forms.TextInput(attrs={'class': 'form-control'}),
        'type_desc': forms.TextInput(attrs={'class': 'form-control'}),
        'power': forms.TextInput(attrs={'class': 'form-control'}),
        'inlet_diameter': forms.TextInput(attrs={'class': 'form-control'}),
        'district_number': forms.TextInput(attrs={'class': 'form-control'}),
        'district_phone': forms.TextInput(attrs={'class': 'form-control'}),
        'subscriber_number': forms.TextInput(attrs={'class': 'form-control'}),
        'meter1_type': forms.TextInput(attrs={'class': 'form-control'}),
        'meter1_number': forms.TextInput(attrs={'class': 'form-control'}),
        'meter1_verification_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'meter2_type': forms.TextInput(attrs={'class': 'form-control'}),
        'meter2_number': forms.TextInput(attrs={'class': 'form-control'}),
        'meter2_verification_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'meter3_type': forms.TextInput(attrs={'class': 'form-control'}),
        'meter3_number': forms.TextInput(attrs={'class': 'form-control'}),
        'meter3_verification_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'network_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        'last_repair_type': forms.TextInput(attrs={'class': 'form-control'}),
        'last_repair_year': forms.NumberInput(attrs={'class': 'form-control'}),
        'installed_power': forms.TextInput(attrs={'class': 'form-control'}),
        'permitted_power': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

BuildingLandscapingFormSet = inlineformset_factory(
    Building, BuildingLandscaping,
    fields=['section', 'element', 'quantity', 'characteristic', 'has_documents', 'condition', 'recommendations'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'element': forms.TextInput(attrs={'class': 'form-control'}),
        'quantity': forms.TextInput(attrs={'class': 'form-control'}),
        'characteristic': forms.TextInput(attrs={'class': 'form-control'}),
        'has_documents': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'condition': forms.TextInput(attrs={'class': 'form-control'}),
        'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    }
)

BuildingInspectionFormSet = inlineformset_factory(
    Building, BuildingInspection,
    fields=['section', 'inspection_date', 'reason', 'inspector', 'findings', 'conclusion', 'recommendations'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'inspection_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'reason': forms.TextInput(attrs={'class': 'form-control'}),
        'inspector': forms.TextInput(attrs={'class': 'form-control'}),
        'findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        'conclusion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    }
)

BuildingRepairFormSet = inlineformset_factory(
    Building, BuildingRepair,
    fields=['section', 'object_name', 'repair_type', 'start_date', 'end_date',
            'contract_number', 'contract_amount', 'contractor', 'warranty_period', 'note'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'object_name': forms.TextInput(attrs={'class': 'form-control'}),
        'repair_type': forms.TextInput(attrs={'class': 'form-control'}),
        'start_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'end_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
        'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
        'contract_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'contractor': forms.TextInput(attrs={'class': 'form-control'}),
        'warranty_period': forms.TextInput(attrs={'class': 'form-control'}),
        'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    }
)

BuildingTenantFormSet = inlineformset_factory(
    Building, BuildingTenant,
    fields=['section', 'name', 'activity', 'rented_areas', 'lease_term', 'contract_number'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'activity': forms.TextInput(attrs={'class': 'form-control'}),
        'rented_areas': forms.TextInput(attrs={'class': 'form-control'}),
        'lease_term': forms.TextInput(attrs={'class': 'form-control'}),
        'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
    }
)

BuildingAppendixFormSet = inlineformset_factory(
    Building, BuildingAppendix,
    fields=['section', 'appendix_type', 'title', 'file'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'appendix_type': forms.Select(attrs={'class': 'form-select'}),
        'title': forms.TextInput(attrs={'class': 'form-control'}),
        'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
    }
)

BuildingDocumentFormSet = inlineformset_factory(
    Building, BuildingDocument,
    fields=['section', 'title', 'file'],
    extra=1, can_delete=True,
    widgets={
        'section': forms.Select(attrs={'class': 'form-select'}),
        'title': forms.TextInput(attrs={'class': 'form-control'}),
        'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
    }
)

BuildingOwnershipDocumentFormSet = inlineformset_factory(
    Building, BuildingOwnershipDocument,
    fields=['title', 'file'],
    extra=1, can_delete=True,
    widgets={
        'title': forms.TextInput(attrs={'class': 'form-control'}),
        'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
    }
)