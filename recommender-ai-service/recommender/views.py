import requests
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .engine import get_recommendations, item_based_similar
from .models import RecommendationCache
from .analytics import build_overview

logger = logging.getLogger(__name__)


class RecommendationView(APIView):
    """
    GET /api/recommendations/<customer_id>/

    Returns a ranked list of recommended books for a customer.
    Uses behavior_dl (Neural CF) when a trained checkpoint exists; otherwise
    collaborative filtering; then popularity for cold users.
    """

    def get(self, request, customer_id):
        limit = int(request.query_params.get("limit", 10))
        refresh = request.query_params.get("refresh", "false").lower() == "true"

        if not refresh:
            cached = list(
                RecommendationCache.objects.filter(
                    customer_id=customer_id
                ).order_by("-score").values_list("book_id", "score")[:limit]
            )
            if cached:
                book_details = self._fetch_book_details([bid for bid, _ in cached])
                results = []
                for book_id, score in cached:
                    detail = book_details.get(book_id, {})
                    results.append({
                        "book_id": book_id,
                        "score": round(score, 4),
                        "title": detail.get("title", ""),
                        "author": detail.get("author", ""),
                        "price": detail.get("price"),
                        "cover_image": detail.get("cover_image", ""),
                        "category_id": detail.get("category_id"),
                    })
                return Response({
                    "customer_id": customer_id,
                    "strategy": "cached",
                    "recommendations": results,
                })

        # Compute fresh recommendations
        recs, strategy = get_recommendations(customer_id, limit)

        # Persist
        RecommendationCache.objects.filter(customer_id=customer_id).delete()
        RecommendationCache.objects.bulk_create([
            RecommendationCache(
                customer_id=customer_id,
                book_id=book_id,
                score=score,
                strategy=strategy,
            )
            for book_id, score in recs
        ])

        book_details = self._fetch_book_details([book_id for book_id, _ in recs])
        results = []
        for book_id, score in recs:
            detail = book_details.get(book_id, {})
            results.append({
                "book_id": book_id,
                "score": round(score, 4),
                "title": detail.get("title", ""),
                "author": detail.get("author", ""),
                "price": detail.get("price"),
                "cover_image": detail.get("cover_image", ""),
                "category_id": detail.get("category_id"),
            })

        return Response({
            "customer_id": customer_id,
            "strategy": strategy,
            "recommendations": results,
        })

    @staticmethod
    def _fetch_book_details(book_ids):
        if not book_ids:
            return {}
        try:
            resp = requests.post(
                f"{settings.BOOK_SERVICE_URL}/internal/books/bulk/",
                json={"ids": book_ids},
                timeout=5,
            )
            resp.raise_for_status()
            return {b["id"]: b for b in resp.json()}
        except requests.RequestException as exc:
            logger.warning("Could not fetch book details: %s", exc)
            return {}


class ItemRecommendationView(APIView):
    """
    GET /api/recommendations/item/<book_id>/

    \"Because you viewed X, you might like Y\" style suggestions.
    """

    def get(self, request, book_id):
        limit = int(request.query_params.get("limit", 8))
        recs = item_based_similar(book_id, limit)
        book_details = RecommendationView._fetch_book_details([bid for bid, _ in recs])
        results = []
        for bid, score in recs:
            detail = book_details.get(bid, {})
            results.append(
                {
                    "book_id": bid,
                    "score": round(score, 4),
                    "title": detail.get("title", ""),
                    "author": detail.get("author", ""),
                    "price": detail.get("price"),
                    "cover_image": detail.get("cover_image", ""),
                    "category_id": detail.get("category_id"),
                }
            )
        return Response(
            {
                "book_id": book_id,
                "recommendations": results,
            }
        )


class AnalyticsOverviewView(APIView):
    """
    GET /api/recommendations/analytics/overview/

    Lightweight analytics for admin/marketing dashboards.
    """

    def get(self, request):
        data = build_overview()
        return Response(data, status=status.HTTP_200_OK)

