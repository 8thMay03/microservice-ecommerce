import logging
from decimal import Decimal
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Order, OrderItem
from .serializers import OrderSerializer, CreateOrderSerializer
from .services import CartServiceClient, PayServiceClient, ShipServiceClient

logger = logging.getLogger(__name__)


class OrderListView(APIView):
    """
    GET  /api/orders/?customer_id=<id>  — list orders for a customer
    POST /api/orders/                   — create an order from the customer's cart
    """

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        qs = Order.objects.prefetch_related("items")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return Response(OrderSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data["customer_id"]

        # If items are passed directly, use them; otherwise fetch from cart-service
        if "items" in data and data["items"]:
            cart_items = [
                {
                    "product_id": it["product_id"],
                    "product_title": it.get("product_title", f"Product #{it['product_id']}"),
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                }
                for it in data["items"]
            ]
        else:
            try:
                cart = CartServiceClient.get_cart(customer_id)
            except Exception:
                return Response(
                    {"error": "Could not reach cart-service. Try again later."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            cart_items = cart.get("items", [])

        if not cart_items:
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        total_amount = sum(
            Decimal(str(item["unit_price"])) * item["quantity"]
            for item in cart_items
        )

        with transaction.atomic():
            order = Order.objects.create(
                customer_id=customer_id,
                total_amount=total_amount,
                shipping_address=data["shipping_address"],
                payment_method=data["payment_method"],
                status=Order.Status.PENDING,
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_id=item["product_id"],
                    product_title=item.get("product_title", f"Product #{item['product_id']}"),
                    quantity=item["quantity"],
                    unit_price=Decimal(str(item["unit_price"])),
                )

        # 3. Process payment
        try:
            payment = PayServiceClient.process_payment(
                order_id=order.id,
                customer_id=customer_id,
                amount=total_amount,
                method=data["payment_method"],
            )
            if payment.get("status") != "COMPLETED":
                order.status = Order.Status.CANCELLED
                order.save()
                return Response(
                    {"error": "Payment failed.", "payment": payment},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )
        except Exception as exc:
            logger.error("Payment service error: %s", exc)
            order.status = Order.Status.CANCELLED
            order.save()
            return Response(
                {"error": "Payment service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        order.status = Order.Status.PAID
        order.save()

        # 4. Create shipment
        try:
            ShipServiceClient.create_shipment(
                order_id=order.id,
                customer_id=customer_id,
                shipping_address=data["shipping_address"],
            )
            order.status = Order.Status.SHIPPED
            order.save()
        except Exception as exc:
            logger.warning("Ship service error (non-fatal): %s", exc)

        # 5. Clear the cart
        CartServiceClient.clear_cart(customer_id)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    """GET/PUT /api/orders/<id>/"""

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
        return Response(OrderSerializer(order).data)

    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.data.get("status")
        if new_status and new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save()
        return Response(OrderSerializer(order).data)
