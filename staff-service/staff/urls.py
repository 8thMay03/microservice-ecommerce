from django.urls import path
from .views import StaffRegisterView, StaffLoginView, StaffListView, StaffDetailView, InventoryManagementView

urlpatterns = [
    path("register/", StaffRegisterView.as_view(), name="staff-register"),
    path("login/", StaffLoginView.as_view(), name="staff-login"),
    path("", StaffListView.as_view(), name="staff-list"),
    path("<int:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    path("inventory/<int:product_id>/", InventoryManagementView.as_view(), name="staff-inventory"),
]
