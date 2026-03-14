from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

from .models import Customer
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerSerializer,
    CustomerUpdateSerializer,
    CustomerLoginSerializer,
)
from .services import CartServiceClient


class RegisterView(APIView):
    """POST /api/customers/register/ — create a new customer account."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            # Trigger cart creation in cart-service
            CartServiceClient.create_cart_for_customer(customer.id)
            tokens = self._get_tokens(customer)
            return Response(
                {"customer": CustomerSerializer(customer).data, "tokens": tokens},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _get_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class LoginView(APIView):
    """POST /api/customers/login/ — authenticate and return JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        customer = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not customer:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(customer)
        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }
        )


class ProfileView(APIView):
    """GET/PUT /api/customers/profile/ — retrieve or update own profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomerSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = CustomerUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CustomerSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerListView(APIView):
    """GET /api/customers/ — list all customers (admin use)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Customer.objects.all().order_by("-created_at")
        return Response(CustomerSerializer(qs, many=True).data)


class CustomerDetailView(APIView):
    """GET /api/customers/<id>/ — fetch customer by ID (admin / internal use)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return Response(CustomerSerializer(customer).data)

    def put(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerUpdateSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CustomerSerializer(customer).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.is_active = False
        customer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
