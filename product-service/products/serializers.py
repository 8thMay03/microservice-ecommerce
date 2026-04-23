from rest_framework import serializers
from .models import Product, ProductInventory


class ProductInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductInventory
        fields = ["stock_quantity", "warehouse_location", "updated_at"]


class ProductSerializer(serializers.ModelSerializer):
    inventory = ProductInventorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "title", "product_type", "sku", "description", "price",
            "cover_image", "category_id", "brand", "attributes",
            "is_active", "inventory", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductWriteSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(write_only=True, default=0)
    warehouse_location = serializers.CharField(write_only=True, default="", allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "title", "product_type", "sku", "description", "price",
            "cover_image", "category_id", "brand", "attributes",
            "is_active", "stock_quantity", "warehouse_location",
        ]

    def create(self, validated_data):
        stock_quantity = validated_data.pop("stock_quantity", 0)
        warehouse_location = validated_data.pop("warehouse_location", "")
        product = Product.objects.create(**validated_data)
        ProductInventory.objects.create(
            product=product,
            stock_quantity=stock_quantity,
            warehouse_location=warehouse_location,
        )
        return product

    def update(self, instance, validated_data):
        stock_quantity = validated_data.pop("stock_quantity", None)
        warehouse_location = validated_data.pop("warehouse_location", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if stock_quantity is not None or warehouse_location is not None:
            inv, _ = ProductInventory.objects.get_or_create(product=instance)
            if stock_quantity is not None:
                inv.stock_quantity = stock_quantity
            if warehouse_location is not None:
                inv.warehouse_location = warehouse_location
            inv.save()
        return instance


class InventoryUpdateSerializer(serializers.Serializer):
    delta = serializers.IntegerField(help_text="Positive to add stock, negative to reduce.")

    def validate_delta(self, value):
        return value
