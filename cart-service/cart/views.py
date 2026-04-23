from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemWriteSerializer, CartItemSerializer


class CartView(APIView):
    """GET /api/cart/{customer_id}/ — retrieve a customer's cart."""

    def get(self, request, customer_id):
        cart = get_object_or_404(Cart.objects.prefetch_related("items"), customer_id=customer_id)
        return Response(CartSerializer(cart).data)


class CartItemView(APIView):
    """POST /api/cart/{customer_id}/items/ — add item to cart."""

    def post(self, request, customer_id):
        cart, _ = Cart.objects.get_or_create(customer_id=customer_id)
        serializer = CartItemWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=data["product_id"],
            defaults={"quantity": data["quantity"], "unit_price": data["unit_price"]},
        )
        if not created:
            item.quantity += data["quantity"]
            item.save()

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    """PUT/DELETE /api/cart/{customer_id}/items/{item_id}/"""

    def put(self, request, customer_id, item_id):
        cart = get_object_or_404(Cart, customer_id=customer_id)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        quantity = request.data.get("quantity")
        if not quantity or int(quantity) < 1:
            return Response({"error": "quantity must be >= 1"}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = int(quantity)
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request, customer_id, item_id):
        cart = get_object_or_404(Cart, customer_id=customer_id)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClearCartView(APIView):
    """DELETE /api/cart/{customer_id}/clear/ — empty cart after checkout."""

    def delete(self, request, customer_id):
        cart = get_object_or_404(Cart, customer_id=customer_id)
        cart.items.all().delete()
        return Response({"message": "Cart cleared."})
