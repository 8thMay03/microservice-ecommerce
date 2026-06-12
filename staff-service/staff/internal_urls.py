from django.urls import path
from .internal_views import InternalStaffListView

urlpatterns = [
    path("", InternalStaffListView.as_view(), name="internal-staff-list"),
]
