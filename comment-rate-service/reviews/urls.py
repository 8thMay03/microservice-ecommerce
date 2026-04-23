from django.urls import path
from .views import RatingListView, ProductRatingSummaryView, CommentListView, CommentDetailView

urlpatterns = [
    path("ratings/", RatingListView.as_view(), name="rating-list"),
    path("ratings/product/<int:product_id>/summary/", ProductRatingSummaryView.as_view(), name="rating-summary"),
    path("comments/", CommentListView.as_view(), name="comment-list"),
    path("comments/<int:pk>/", CommentDetailView.as_view(), name="comment-detail"),
]
