# requests_app/services/material_service.py
from decimal import Decimal
from ..models import Material, UsedMaterial


class MaterialService:
    """Сервис для управления материалами на складе."""

    @staticmethod
    def get_material_stock():
        """Возвращает все материалы, отсортированные по названию."""
        return Material.objects.all().order_by('name')

    @staticmethod
    def create_material(data):
        """Создаёт новый материал."""
        return Material.objects.create(**data)

    @staticmethod
    def update_material(material, data):
        """Обновляет существующий материал."""
        for attr, value in data.items():
            setattr(material, attr, value)
        material.save()
        return material

    @staticmethod
    def delete_material(material):
        """Удаляет материал."""
        material.delete()

    @staticmethod
    def reduce_stock(material, quantity):
        """Уменьшает количество материала на складе."""
        if material.quantity_in_stock < quantity:
            raise ValueError(f'Недостаточно материала "{material.name}" на складе')
        material.quantity_in_stock -= quantity
        material.save()
        return material

    @staticmethod
    def add_stock(material, quantity):
        """Увеличивает количество материала на складе."""
        material.quantity_in_stock += quantity
        material.save()
        return material

    @staticmethod
    def get_materials_for_export():
        """
        Возвращает все материалы в виде списка словарей для экспорта.
        """
        return Material.objects.all().values('name', 'unit', 'quantity_in_stock', 'default_price')