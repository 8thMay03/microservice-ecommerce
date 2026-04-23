"""
Recommendation engine.

Strategy 1 — Collaborative Filtering (user-based):
  Build a customer × product purchase matrix from order history.
  Find the k nearest customers using cosine similarity.
  Recommend products those neighbours bought that the target customer hasn't.

Strategy 2 — Popularity Fallback:
  When the target customer has no history, return the most-purchased products overall.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _fetch_all_orders() -> List[dict]:
    """Fetch all orders from order-service; we keep only PAID/SHIPPED/DELIVERED for the matrix."""
    try:
        resp = requests.get(
            f"{settings.ORDER_SERVICE_URL}/api/orders/",
            timeout=10,
        )
        resp.raise_for_status()
        orders = resp.json()
        completed = {
            "PAID",
            "SHIPPED",
            "DELIVERED",
        }
        return [o for o in orders if o.get("status") in completed]
    except requests.RequestException as exc:
        logger.error("Failed to fetch orders: %s", exc)
        return []


def _fetch_customer_orders(customer_id: int) -> List[dict]:
    try:
        resp = requests.get(
            f"{settings.ORDER_SERVICE_URL}/internal/orders/customer/{customer_id}/history/",
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch orders for customer %s: %s", customer_id, exc)
        return []


def _extract_product_ids_from_orders(orders: List[dict]) -> List[int]:
    product_ids = []
    for order in orders:
        for item in order.get("items", []):
            product_ids.append(item["product_id"])
    return list(set(product_ids))


def _fetch_product_categories(product_ids: List[int]) -> Dict[int, int]:
    """Return {product_id: category_id} using product-service internal bulk API."""
    if not product_ids:
        return {}
    try:
        resp = requests.post(
            f"{settings.PRODUCT_SERVICE_URL}/internal/products/bulk/",
            json={"ids": product_ids},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return {p["id"]: p.get("category_id") for p in data}
    except requests.RequestException as exc:
        logger.warning("Failed to fetch product categories: %s", exc)
        return {}


def _fetch_rating_scores(product_ids: List[int]) -> Dict[int, float]:
    """
    Return {product_id: rating_factor} where factor in [0.7, 1.1].
    Uses average rating from comment-rate-service; neutral (1.0) if no data.
    """
    if not product_ids:
        return {}

    factors: Dict[int, float] = {}
    for product_id in product_ids:
        try:
            resp = requests.get(
                f"{settings.COMMENT_RATE_SERVICE_URL}/api/reviews/ratings/product/{product_id}/summary/",
                timeout=3,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            avg = data.get("average_score") or 0
            # Normalize 0–5 → 0–1, then map to [0.7, 1.1]
            norm = max(0.0, min(1.0, float(avg) / 5.0))
            factors[product_id] = 0.7 + 0.4 * norm
        except requests.RequestException:
            continue
        except (TypeError, ValueError):
            continue
    return factors


def _apply_rating_boost(scores: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
    """Multiply base scores by rating factor."""
    if not scores:
        return scores
    product_ids = [pid for pid, _ in scores]
    rating_factors = _fetch_rating_scores(product_ids)
    boosted: List[Tuple[int, float]] = []
    for product_id, base in scores:
        factor = rating_factors.get(product_id, 1.0)
        boosted.append((product_id, base * factor))
    # Re-normalize to [0,1]
    if not boosted:
        return scores
    max_score = max(s for _, s in boosted) or 1.0
    return [(pid, s / max_score) for pid, s in boosted]


def _apply_category_preference(
    customer_id: int,
    scores: List[Tuple[int, float]],
    customer_products: Dict[int, set],
) -> List[Tuple[int, float]]:
    """
    Slightly boost products that belong to categories the customer buys a lot.
    """
    if not scores or customer_id not in customer_products:
        return scores

    purchased_product_ids = list(customer_products[customer_id])
    cat_map = _fetch_product_categories(
        list({*purchased_product_ids, *[pid for pid, _ in scores]})
    )
    if not cat_map:
        return scores

    # Count categories in customer's history
    cat_counts: Dict[int, int] = defaultdict(int)
    for pid in purchased_product_ids:
        cat_id = cat_map.get(pid)
        if cat_id is not None:
            cat_counts[cat_id] += 1
    if not cat_counts:
        return scores

    max_count = max(cat_counts.values()) or 1
    boosted: List[Tuple[int, float]] = []
    for product_id, base in scores:
        cat_id = cat_map.get(product_id)
        if cat_id is None or cat_id not in cat_counts:
            boosted.append((product_id, base))
            continue
        pref = cat_counts[cat_id] / max_count  # 0–1
        factor = 1.0 + 0.2 * pref  # up to +20%
        boosted.append((product_id, base * factor))

    max_score = max(s for _, s in boosted) or 1.0
    return [(pid, s / max_score) for pid, s in boosted]


def _deep_learning_recommendations(
    customer_id: int, limit: int
) -> Optional[List[Tuple[int, float]]]:
    """
    Neural CF (model_behavior) over completed orders; None if no checkpoint
    or user/product out of vocabulary.
    """
    from . import model_behavior as mb

    purchased: Set[int] = set()
    for order in _fetch_customer_orders(customer_id):
        for item in order.get("items", []):
            purchased.add(item["product_id"])

    pool = max(limit * 5, 20)
    raw = mb.recommend_from_behavior_model(customer_id, purchased, pool)
    if not raw:
        return None

    max_score = max(s for _, s in raw) or 1.0
    normalized = [(product_id, s / max_score) for product_id, s in raw]

    all_orders = _fetch_all_orders()
    customer_products: dict = defaultdict(set)
    for order in all_orders:
        cid = order.get("customer_id")
        for item in order.get("items", []):
            customer_products[cid].add(item["product_id"])

    boosted = _apply_rating_boost(normalized)
    boosted = _apply_category_preference(customer_id, boosted, customer_products)
    boosted.sort(key=lambda x: x[1], reverse=True)
    return boosted[:limit]


def popularity_based(limit: int = 10) -> List[Tuple[int, float]]:
    """Return (product_id, score) tuples ranked by purchase frequency, boosted by rating."""
    orders = _fetch_all_orders()
    counts: dict = defaultdict(int)
    for order in orders:
        for item in order.get("items", []):
            counts[item["product_id"]] += item.get("quantity", 1)
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    if not ranked:
        return []
    max_count = ranked[0][1] or 1
    base_scores = [(product_id, count / max_count) for product_id, count in ranked]
    return _apply_rating_boost(base_scores)


def collaborative_filtering(customer_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    """User-based collaborative filtering using cosine similarity."""
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("numpy/sklearn not available; falling back to popularity.")
        return popularity_based(limit)

    # Build customer → set of purchased product_ids
    all_orders = _fetch_all_orders()
    customer_products: dict = defaultdict(set)
    for order in all_orders:
        cid = order.get("customer_id")
        for item in order.get("items", []):
            customer_products[cid].add(item["product_id"])

    if not customer_products:
        return popularity_based(limit)

    all_product_ids = sorted({p for products in customer_products.values() for p in products})
    if not all_product_ids:
        return popularity_based(limit)

    product_index = {p: i for i, p in enumerate(all_product_ids)}
    customer_ids = sorted(customer_products.keys())
    customer_index = {c: i for i, c in enumerate(customer_ids)}

    matrix = np.zeros((len(customer_ids), len(all_product_ids)), dtype=np.float32)
    for cid, products in customer_products.items():
        for product in products:
            matrix[customer_index[cid], product_index[product]] = 1.0

    if customer_id not in customer_index:
        return popularity_based(limit)

    target_vec = matrix[customer_index[customer_id]].reshape(1, -1)
    similarities = cosine_similarity(target_vec, matrix)[0]
    already_purchased = customer_products[customer_id]

    candidate_scores: dict = defaultdict(float)
    for i, sim in enumerate(similarities):
        if customer_ids[i] == customer_id or sim <= 0:
            continue
        for product_id in customer_products[customer_ids[i]]:
            if product_id not in already_purchased:
                candidate_scores[product_id] += sim

    if not candidate_scores:
        return popularity_based(limit)

    ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    if not ranked:
        return []

    max_score = ranked[0][1] or 1
    base_scores = [(product_id, score / max_score) for product_id, score in ranked]

    # 1) boost by product rating
    boosted = _apply_rating_boost(base_scores)
    # 2) boost by customer's preferred categories
    boosted = _apply_category_preference(customer_id, boosted, customer_products)
    return boosted


def get_recommendations(
    customer_id: int, limit: int = 10
) -> Tuple[List[Tuple[int, float]], str]:
    """
    Prefer trained behavior_dl checkpoint when available; else collaborative
    filtering; else popularity. Returns (ranked list, strategy name).
    """
    dl = _deep_learning_recommendations(customer_id, limit)
    if dl:
        return dl, "behavior_dl"

    results = collaborative_filtering(customer_id, limit)
    if not results:
        return popularity_based(limit), "popularity"
    return results, "collaborative_filtering"


def item_based_similar(product_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    """
    Simple item-based recommendation: products often bought together with `product_id`.
    """
    orders = _fetch_all_orders()
    co_counts: Dict[int, int] = defaultdict(int)
    for order in orders:
        items = [it["product_id"] for it in order.get("items", [])]
        if product_id not in items:
            continue
        for other in items:
            if other == product_id:
                continue
            co_counts[other] += 1

    if not co_counts:
        return popularity_based(limit)

    ranked = sorted(co_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    max_count = ranked[0][1] or 1
    base_scores = [(pid, c / max_count) for pid, c in ranked]
    # Boost by ratings as well
    return _apply_rating_boost(base_scores)
