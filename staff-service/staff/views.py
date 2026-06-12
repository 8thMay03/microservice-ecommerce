import requests
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import StaffMember
from .serializers import StaffRegistrationSerializer, StaffSerializer, StaffLoginSerializer

logger = logging.getLogger(__name__)


class StaffRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StaffRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save()
            refresh = RefreshToken.for_user(member)
            return Response(
                {
                    "staff": StaffSerializer(member).data,
                    "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StaffLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        member = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not member:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(member)
        return Response({
            "staff": StaffSerializer(member).data,
            "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
        })


class StaffListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        members = StaffMember.objects.filter(is_active=True)
        return Response(StaffSerializer(members, many=True).data)


class StaffDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        member = get_object_or_404(StaffMember, pk=pk)
        return Response(StaffSerializer(member).data)

    def put(self, request, pk):
        member = get_object_or_404(StaffMember, pk=pk)
        serializer = StaffSerializer(member, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        member = get_object_or_404(StaffMember, pk=pk)
        member.is_active = False
        member.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryManagementView(APIView):
    """Staff action: adjust product stock via product-service."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, product_id):
        delta = request.data.get("delta")
        if delta is None:
            return Response({"error": "delta is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resp = requests.patch(
                f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/inventory/",
                json={"delta": int(delta)},
                timeout=5,
            )
            return Response(resp.json(), status=resp.status_code)
        except requests.RequestException as exc:
            logger.error("product-service inventory update failed: %s", exc)
            return Response({"error": "product-service unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
