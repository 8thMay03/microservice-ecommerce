from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "product_title", "quantity", "unit_price", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "customer_id", "status", "total_amount",
            "shipping_address", "payment_method", "items",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_title = serializers.CharField(max_length=300, default="")
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CreateOrderSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    shipping_address = serializers.CharField()
    payment_method = serializers.CharField(default="CREDIT_CARD")
    items = CreateOrderItemSerializer(many=True, required=False)
