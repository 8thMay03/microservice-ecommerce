from django.urls import path
from .views import (
    ManagerRegisterView, ManagerLoginView,
    SalesReportView, StaffReportView, CustomerReportView,
)

urlpatterns = [
    path("register/", ManagerRegisterView.as_view(), name="manager-register"),
    path("login/", ManagerLoginView.as_view(), name="manager-login"),
    path("reports/sales/", SalesReportView.as_view(), name="manager-sales-report"),
    path("reports/staff/", StaffReportView.as_view(), name="manager-staff-report"),
    path("reports/customers/", CustomerReportView.as_view(), name="manager-customer-report"),
]
