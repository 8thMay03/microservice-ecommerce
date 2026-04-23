from django.urls import path
from .internal_views import InternalTopRatedProductsView

urlpatterns = [
    path("top-rated/", InternalTopRatedProductsView.as_view(), name="internal-top-rated"),
]
