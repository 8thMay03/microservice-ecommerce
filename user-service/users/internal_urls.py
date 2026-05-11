from django.urls import path
from . import internal_views

urlpatterns = [
    path("<int:pk>/", internal_views.InternalUserDetailView.as_view(), name="internal-user-detail"),
    path("", internal_views.InternalUserListView.as_view(), name="internal-user-list"),
    path("staff/", internal_views.InternalStaffListView.as_view(), name="internal-staff-list"),
]
