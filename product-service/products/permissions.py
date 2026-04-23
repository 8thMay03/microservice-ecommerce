from rest_framework import permissions


class IsManagerOrReadOnly(permissions.BasePermission):
    """Allow read for anyone; write (POST, PUT, PATCH, DELETE) only for authenticated managers."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and getattr(request.user, "is_authenticated", False)
