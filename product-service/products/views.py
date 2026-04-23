from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Product, ProductInventory
from .serializers import ProductSerializer, ProductWriteSerializer, InventoryUpdateSerializer
from .auth import ManagerJWTAuthentication
from .permissions import IsManagerOrReadOnly


class ProductListView(APIView):
    authentication_classes = [ManagerJWTAuthentication]
    permission_classes = [IsManagerOrReadOnly]
    """GET /api/products/ — list products with optional filters."""

    def get(self, request):
        qs = Product.objects.select_related("inventory").all()
        if not (request.user and getattr(request.user, "is_authenticated", False)):
            qs = qs.filter(is_active=True)

        category_id = request.query_params.get("category_id")
        product_type = request.query_params.get("product_type")
        search = request.query_params.get("search")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        if category_id:
            qs = qs.filter(category_id=category_id)
        if product_type:
            qs = qs.filter(product_type=product_type)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(brand__icontains=search))
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)

        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()
        products = qs[start:end]
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": ProductSerializer(products, many=True).data,
        })

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(APIView):
    """GET/PUT/DELETE /api/products/<id>/"""
    authentication_classes = [ManagerJWTAuthentication]
    permission_classes = [IsManagerOrReadOnly]

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("inventory"), pk=pk)
        return Response(ProductSerializer(product).data)

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            product = serializer.save()
            return Response(ProductSerializer(product).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = False
        product.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InventoryUpdateView(APIView):
    """PATCH /api/products/<id>/inventory/ — adjust stock quantity."""
    authentication_classes = [ManagerJWTAuthentication]
    permission_classes = [IsManagerOrReadOnly]

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = InventoryUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        delta = serializer.validated_data["delta"]
        inv, _ = ProductInventory.objects.get_or_create(product=product)
        new_qty = inv.stock_quantity + delta
        if new_qty < 0:
            return Response(
                {"error": "Insufficient stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inv.stock_quantity = new_qty
        inv.save()
        return Response({"product_id": product.id, "stock_quantity": inv.stock_quantity})
