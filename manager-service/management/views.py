import requests
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.conf import settings

from .models import ManagerUser
from .serializers import ManagerSerializer, ManagerRegistrationSerializer, ManagerLoginSerializer

logger = logging.getLogger(__name__)


class ManagerRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ManagerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            manager = serializer.save()
            refresh = RefreshToken.for_user(manager)
            return Response(
                {
                    "manager": ManagerSerializer(manager).data,
                    "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagerLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ManagerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        manager = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not manager:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(manager)
        return Response({
            "manager": ManagerSerializer(manager).data,
            "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
        })


class SalesReportView(APIView):
    """GET /api/managers/reports/sales/ — aggregated order totals."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            resp = requests.get(
                f"{settings.ORDER_SERVICE_URL}/api/orders/",
                timeout=10,
            )
            resp.raise_for_status()
            orders = resp.json()
        except requests.RequestException as exc:
            logger.error("order-service error: %s", exc)
            return Response({"error": "order-service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        total_revenue = sum(float(o.get("total_amount", 0)) for o in orders)
        status_counts: dict = {}
        for order in orders:
            s = order.get("status", "UNKNOWN")
            status_counts[s] = status_counts.get(s, 0) + 1

        return Response({
            "total_orders": len(orders),
            "total_revenue": round(total_revenue, 2),
            "orders_by_status": status_counts,
        })


class StaffReportView(APIView):
    """GET /api/managers/reports/staff/ — staff roster from staff-service."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            resp = requests.get(
                f"{settings.STAFF_SERVICE_URL}/internal/staff/",
                timeout=5,
            )
            resp.raise_for_status()
            return Response({"staff_count": len(resp.json()), "staff": resp.json()})
        except requests.RequestException as exc:
            logger.error("staff-service error: %s", exc)
            return Response({"error": "staff-service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class CustomerReportView(APIView):
    """GET /api/managers/reports/customers/?id=<id>"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_id = request.query_params.get("id")
        if not customer_id:
            return Response({"error": "id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resp = requests.get(
                f"{settings.CUSTOMER_SERVICE_URL}/internal/customers/{customer_id}/",
                timeout=5,
            )
            resp.raise_for_status()
            return Response(resp.json())
        except requests.RequestException as exc:
            logger.error("customer-service error: %s", exc)
            return Response({"error": "customer-service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
