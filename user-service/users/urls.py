from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="user-register"),
    path("profile/", views.ProfileView.as_view(), name="user-profile"),
    path("", views.UserListView.as_view(), name="user-list"),
    path("<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("inventory/<int:product_id>/", views.InventoryManagementView.as_view(), name="user-inventory"),
    path("reports/sales/", views.SalesReportView.as_view(), name="user-sales-report"),
    path("reports/staff/", views.StaffReportView.as_view(), name="user-staff-report"),
    path("reports/customers/", views.CustomerReportView.as_view(), name="user-customer-report"),
]
