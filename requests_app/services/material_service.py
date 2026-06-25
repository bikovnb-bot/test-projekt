# requests_app/services/material_service.py
from decimal import Decimal
from ..models import Material, UsedMaterial, MaterialTransaction
from .notification_service import NotificationService


class MaterialService:
    """Сервис для управления материалами на складе."""

    @staticmethod
    def get_material_stock():
        return Material.objects.all().order_by('name')

    @staticmethod
    def create_material(data):
        return Material.objects.create(**data)

    @staticmethod
    def update_material(material, data):
        for attr, value in data.items():
            setattr(material, attr, value)
        material.save()
        return material

    @staticmethod
    def delete_material(material):
        material.delete()

    @staticmethod
    def reduce_stock(material, quantity, request=None, comment=''):
        if material.quantity_in_stock < quantity:
            raise ValueError(f'Недостаточно материала "{material.name}" на складе')
        material.quantity_in_stock -= quantity
        material.save()
        MaterialTransaction.objects.create(
            material=material,
            request=request,
            quantity=quantity,
            transaction_type='out',
            comment=comment
        )
        # Проверяем, не упал ли остаток ниже минимального
        if material.is_low_stock():
            NotificationService.send_telegram(
                f"⚠️ Внимание! Остаток материала '{material.name}' ниже минимального "
                f"({material.quantity_in_stock} < {material.min_stock})"
            )
        return material

    @staticmethod
    def add_stock(material, quantity, request=None, comment=''):
        material.quantity_in_stock += quantity
        material.save()
        MaterialTransaction.objects.create(
            material=material,
            request=request,
            quantity=quantity,
            transaction_type='in',
            comment=comment
        )
        return material

    @staticmethod
    def get_materials_for_export():
        return Material.objects.all().values('name', 'unit', 'quantity_in_stock', 'default_price', 'min_stock')

    @staticmethod
    def get_transactions(material):
        """Возвращает все транзакции для материала, отсортированные по дате (сначала новые)."""
        return material.transactions.all().order_by('-created_at')

    @staticmethod
    def adjust_stock(material, quantity, transaction_type, comment='', request=None):
        """
        Ручная корректировка остатка (приход или списание).
        transaction_type: 'in' или 'out'
        """
        if transaction_type not in ['in', 'out']:
            raise ValueError("Некорректный тип транзакции")
        if transaction_type == 'out':
            return MaterialService.reduce_stock(material, quantity, request, comment)
        else:
            return MaterialService.add_stock(material, quantity, request, comment)