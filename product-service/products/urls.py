from django.urls import path
from .views import ProductListView, ProductDetailView, InventoryUpdateView

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("<int:pk>/inventory/", InventoryUpdateView.as_view(), name="product-inventory"),
]
