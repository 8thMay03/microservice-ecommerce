from django.urls import path
from .internal_views import InternalProductDetailView, InternalBulkDetailView

urlpatterns = [
    path("<int:pk>/", InternalProductDetailView.as_view(), name="internal-product-detail"),
    path("bulk/", InternalBulkDetailView.as_view(), name="internal-bulk-detail"),
]
