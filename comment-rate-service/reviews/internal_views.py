from django.db.models import Avg, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Rating


class InternalTopRatedProductsView(APIView):
    """Returns top-rated product IDs for the recommender-ai-service."""
    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        top_products = (
            Rating.objects
            .values("product_id")
            .annotate(avg_score=Avg("score"), total=Count("id"))
            .filter(total__gte=1)
            .order_by("-avg_score", "-total")[:limit]
        )
        return Response(list(top_products))
