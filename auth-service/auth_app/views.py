from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer, LoginSerializer
from .jwt_utils import get_tokens_for_user
from .services import CartServiceClient


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create cart for customers
        if user.role == "CUSTOMER":
            CartServiceClient.create_cart_for_customer(user.id)

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.lower(),
                },
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)
        if user is None:
            try:
                lookup_user = User.objects.get(email=email)
                if not lookup_user.is_active:
                    return Response(
                        {"detail": "Account is deactivated."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except User.DoesNotExist:
                pass
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.lower(),
                },
                "tokens": tokens,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            return Response(
                {
                    "access": str(token.access_token),
                    "refresh": str(token),
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
