from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .models import Product
from .serializers import ProductSerializer


class InternalProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("inventory"), pk=pk)
        return Response(ProductSerializer(product).data)


class InternalBulkDetailView(APIView):
    """POST /internal/products/bulk/ — fetch multiple products by IDs."""
    permission_classes = [AllowAny]

    def post(self, request):
        ids = request.data.get("ids", [])
        products = Product.objects.select_related("inventory").filter(id__in=ids)
        return Response(ProductSerializer(products, many=True).data)
