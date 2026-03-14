from django.urls import path
from .views import RegisterView, LoginView, ProfileView, CustomerListView, CustomerDetailView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="customer-register"),
    path("login/", LoginView.as_view(), name="customer-login"),
    path("profile/", ProfileView.as_view(), name="customer-profile"),
    path("", CustomerListView.as_view(), name="customer-list"),
    path("<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]
