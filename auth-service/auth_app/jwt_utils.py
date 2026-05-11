from rest_framework_simplejwt.tokens import RefreshToken


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email
    refresh.access_token["role"] = user.role
    refresh.access_token["email"] = user.email
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
