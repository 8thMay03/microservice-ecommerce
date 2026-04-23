"""Internal APIs for service-to-service calls (e.g. Neo4j graph ETL)."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category


class InternalCategoriesFlatView(APIView):
    """
    GET /internal/catalog/categories/all/

    Returns every category row (roots + all subcategories) as a flat list
    so downstream services can build a full tree in Neo4j without walking nested JSON.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        rows = []
        for c in Category.objects.all().order_by("id"):
            rows.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "parent_id": c.parent_id,
                }
            )
        return Response(rows)
