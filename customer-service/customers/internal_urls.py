from django.urls import path
from .internal_views import InternalCustomerDetailView

urlpatterns = [
    path("<int:pk>/", InternalCustomerDetailView.as_view(), name="internal-customer-detail"),
]
