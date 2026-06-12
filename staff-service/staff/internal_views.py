from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import StaffMember
from .serializers import StaffSerializer


class InternalStaffListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        members = StaffMember.objects.filter(is_active=True)
        return Response(StaffSerializer(members, many=True).data)
