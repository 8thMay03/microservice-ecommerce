import requests
from django.conf import settings
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    StaffCreateSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create cart for customer
        if user.role == "CUSTOMER":
            try:
                cart_url = getattr(settings, "CART_SERVICE_URL", "http://cart-service:8000")
                requests.post(
                    f"{cart_url}/internal/carts/create/",
                    json={"customer_id": user.id},
                    timeout=5,
                )
            except requests.RequestException:
                pass

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = User.objects.filter(is_active=True).order_by("-created_at")
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role.upper())
        return queryset


class UserDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def put(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, product_id):
        delta = request.data.get("delta")
        if delta is None:
            return Response(
                {"detail": "delta is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product_url = getattr(settings, "PRODUCT_SERVICE_URL", "http://product-service:8000")
        try:
            resp = requests.patch(
                f"{product_url}/api/products/{product_id}/inventory/",
                json={"delta": int(delta)},
                headers={"Authorization": request.META.get("HTTP_AUTHORIZATION", "")},
                timeout=5,
            )
            return Response(resp.json(), status=resp.status_code)
        except requests.RequestException:
            return Response(
                {"detail": "Product service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class SalesReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        order_url = getattr(settings, "ORDER_SERVICE_URL", "http://order-service:8000")
        try:
            resp = requests.get(
                f"{order_url}/api/orders/",
                headers={"Authorization": request.META.get("HTTP_AUTHORIZATION", "")},
                timeout=10,
            )
            orders = resp.json()
            if isinstance(orders, dict):
                orders = orders.get("results", [])

            total_orders = len(orders)
            total_revenue = sum(float(o.get("total_amount", 0)) for o in orders)
            orders_by_status = {}
            for o in orders:
                s = o.get("status", "UNKNOWN")
                orders_by_status[s] = orders_by_status.get(s, 0) + 1

            return Response({
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "orders_by_status": orders_by_status,
            })
        except requests.RequestException:
            return Response(
                {"detail": "Order service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class StaffReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        staff = User.objects.filter(role="STAFF", is_active=True)
        return Response({
            "staff_count": staff.count(),
            "staff": UserSerializer(staff, many=True).data,
        })


class CustomerReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("id")
        if not customer_id:
            return Response(
                {"detail": "id query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(pk=customer_id, role="CUSTOMER")
        except User.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserSerializer(user).data)
