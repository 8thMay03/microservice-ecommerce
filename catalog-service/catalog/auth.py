"""
Validates JWT tokens issued by auth-service.
"""
import jwt
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions


class ManagerJWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith(f"{self.keyword} "):
            return None

        token = auth_header[len(self.keyword) + 1 :].strip()
        secret = getattr(settings, "JWT_SECRET_KEY", None)
        if not secret:
            raise exceptions.AuthenticationFailed("JWT not configured.")

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        role = payload.get("role", "")
        if role not in ("STAFF", "MANAGER"):
            raise exceptions.AuthenticationFailed("Staff or manager access required.")

        user = type(
            "User",
            (),
            {
                "is_authenticated": True,
                "id": payload.get("user_id"),
                "role": role,
            },
        )()
        return (user, token)
