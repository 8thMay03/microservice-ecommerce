from django.urls import path

from .internal_views import InternalCategoriesFlatView

urlpatterns = [
    path(
        "categories/all/",
        InternalCategoriesFlatView.as_view(),
        name="internal-categories-flat",
    ),
]
