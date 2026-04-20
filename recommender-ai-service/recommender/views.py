import requests
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .engine import get_recommendations, item_based_similar
from .models import CustomerBehaviorEvent, RecommendationCache
from .analytics import build_overview

logger = logging.getLogger(__name__)


def _recommendation_payload_rows(pairs, product_details):
    """Build API rows; skip product_ids missing from product_details (stale / deleted)."""
    rows = []
    for product_id, score in pairs:
        if product_id not in product_details:
            continue
        detail = product_details[product_id]
        rows.append({
            "product_id": product_id,
            "score": round(score, 4),
            "title": detail.get("title", ""),
            "brand": detail.get("brand", ""),
            "price": detail.get("price"),
            "cover_image": detail.get("cover_image", ""),
            "category_id": detail.get("category_id"),
            "product_type": detail.get("product_type", ""),
        })
    return rows


class BehaviorEventView(APIView):
    """
    POST /api/recommendations/events/

    Records storefront signals for behavior-aware model training.
    Body: {"customer_id": int, "product_id": int, "event_type": "view"|"click"|"add_to_cart"}
    """

    def post(self, request):
        body = request.data
        try:
            customer_id = int(body["customer_id"])
            product_id = int(body["product_id"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"error": "customer_id and product_id are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = str(body.get("event_type") or "").strip().lower()
        allowed = {c[0] for c in CustomerBehaviorEvent.EventType.choices}
        if raw not in allowed:
            return Response(
                {"error": "event_type must be one of: view, click, add_to_cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        CustomerBehaviorEvent.objects.create(
            customer_id=customer_id,
            product_id=product_id,
            event_type=raw,
        )
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class RecommendationView(APIView):
    """
    GET /api/recommendations/<customer_id>/

    Returns a ranked list of recommended products for a customer.
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
                ).order_by("-score").values_list("product_id", "score")[:limit]
            )
            if cached:
                product_details = self._fetch_product_details([pid for pid, _ in cached])
                results = _recommendation_payload_rows(cached, product_details)
                if results:
                    return Response({
                        "customer_id": customer_id,
                        "strategy": "cached",
                        "recommendations": results,
                    })
                # Cache only had stale IDs (e.g. after DB reseed); fall through and recompute.

        # Compute fresh recommendations
        recs, strategy = get_recommendations(customer_id, limit)

        product_details = self._fetch_product_details([product_id for product_id, _ in recs])
        recs = [(pid, s) for pid, s in recs if pid in product_details]

        # Persist only rows that still exist in product-service
        RecommendationCache.objects.filter(customer_id=customer_id).delete()
        if recs:
            RecommendationCache.objects.bulk_create([
                RecommendationCache(
                    customer_id=customer_id,
                    product_id=product_id,
                    score=score,
                    strategy=strategy,
                )
                for product_id, score in recs
            ])

        results = _recommendation_payload_rows(recs, product_details)

        return Response({
            "customer_id": customer_id,
            "strategy": strategy,
            "recommendations": results,
        })

    @staticmethod
    def _fetch_product_details(product_ids):
        if not product_ids:
            return {}
        try:
            resp = requests.post(
                f"{settings.PRODUCT_SERVICE_URL}/internal/products/bulk/",
                json={"ids": product_ids},
                timeout=5,
            )
            resp.raise_for_status()
            return {p["id"]: p for p in resp.json()}
        except requests.RequestException as exc:
            logger.warning("Could not fetch product details: %s", exc)
            return {}


class ItemRecommendationView(APIView):
    """
    GET /api/recommendations/item/<product_id>/

    \"Because you viewed X, you might like Y\" style suggestions.
    """

    def get(self, request, product_id):
        limit = int(request.query_params.get("limit", 8))
        recs = item_based_similar(product_id, limit)
        product_details = RecommendationView._fetch_product_details([pid for pid, _ in recs])
        recs = [(pid, s) for pid, s in recs if pid in product_details]
        results = _recommendation_payload_rows(recs, product_details)
        return Response(
            {
                "product_id": product_id,
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
