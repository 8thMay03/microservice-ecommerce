from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer


class InternalUserDetailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)
        return Response(UserSerializer(user).data)


class InternalUserListView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        queryset = User.objects.filter(is_active=True)
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role.upper())
        return Response(UserSerializer(queryset, many=True).data)


class InternalStaffListView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        staff = User.objects.filter(role="STAFF", is_active=True)
        return Response(UserSerializer(staff, many=True).data)
