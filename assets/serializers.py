from rest_framework import serializers
from .models import Asset, AssetCheck

class AssetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'inventory_number', 'name']

class InventorySyncSerializer(serializers.Serializer):
    inventory_numbers = serializers.ListField(child=serializers.CharField())