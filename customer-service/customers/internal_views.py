from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Customer
from .serializers import CustomerSerializer


class InternalCustomerDetailView(APIView):
    """Internal endpoint — no JWT required, called only by peer services."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        return Response(CustomerSerializer(customer).data)
