"""
Validates JWT tokens issued by manager-service or staff-service.
Used for admin/staff write operations (POST, PUT, PATCH, DELETE).
"""
import jwt
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions


class ManagerJWTAuthentication(authentication.BaseAuthentication):
    """
    Validates Bearer token from manager-service or staff-service.
    Sets request.user to a simple object with is_authenticated=True if valid.
    """
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith(f"{self.keyword} "):
            return None

        token = auth_header[len(self.keyword) + 1 :].strip()
        secrets = [
            getattr(settings, "MANAGER_JWT_SECRET", None),
            getattr(settings, "STAFF_JWT_SECRET", None),
        ]
        secrets = [s for s in secrets if s]

        for secret in secrets:
            try:
                payload = jwt.decode(
                    token,
                    secret,
                    algorithms=["HS256"],
                    options={"verify_exp": True},
                )
                user = type("Manager", (), {"is_authenticated": True, "id": payload.get("user_id")})()
                return (user, token)
            except jwt.InvalidTokenError:
                continue

        raise exceptions.AuthenticationFailed("Invalid or expired token.")
