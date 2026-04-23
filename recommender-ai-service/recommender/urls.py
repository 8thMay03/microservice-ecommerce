from django.urls import path
from .views import RecommendationView, ItemRecommendationView, AnalyticsOverviewView

urlpatterns = [
    path("<int:customer_id>/", RecommendationView.as_view(), name="recommendations"),
    path("item/<int:product_id>/", ItemRecommendationView.as_view(), name="item-recommendations"),
    path("analytics/overview/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
]
