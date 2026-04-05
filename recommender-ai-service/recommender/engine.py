"""
Recommendation engine.

Strategy 1 — Collaborative Filtering (user-based):
  Build a customer × book purchase matrix from order history.
  Find the k nearest customers using cosine similarity.
  Recommend books those neighbours bought that the target customer hasn't.

Strategy 2 — Popularity Fallback:
  When the target customer has no history, return the most-purchased books overall.
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


def _extract_book_ids_from_orders(orders: List[dict]) -> List[int]:
    book_ids = []
    for order in orders:
        for item in order.get("items", []):
            book_ids.append(item["book_id"])
    return list(set(book_ids))


def _fetch_book_categories(book_ids: List[int]) -> Dict[int, int]:
    """Return {book_id: category_id} using book-service internal bulk API."""
    if not book_ids:
        return {}
    try:
        resp = requests.post(
            f"{settings.BOOK_SERVICE_URL}/internal/books/bulk/",
            json={"ids": book_ids},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        return {b["id"]: b.get("category_id") for b in data}
    except requests.RequestException as exc:
        logger.warning("Failed to fetch book categories: %s", exc)
        return {}


def _fetch_rating_scores(book_ids: List[int]) -> Dict[int, float]:
    """
    Return {book_id: rating_factor} where factor in [0.7, 1.1].
    Uses average rating from comment-rate-service; neutral (1.0) if no data.
    """
    if not book_ids:
        return {}

    factors: Dict[int, float] = {}
    for book_id in book_ids:
        try:
            resp = requests.get(
                f"{settings.COMMENT_RATE_SERVICE_URL}/api/reviews/ratings/book/{book_id}/summary/",
                timeout=3,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            avg = data.get("average_score") or 0
            # Normalize 0–5 → 0–1, then map to [0.7, 1.1]
            norm = max(0.0, min(1.0, float(avg) / 5.0))
            factors[book_id] = 0.7 + 0.4 * norm
        except requests.RequestException:
            continue
        except (TypeError, ValueError):
            continue
    return factors


def _apply_rating_boost(scores: List[Tuple[int, float]]) -> List[Tuple[int, float]]:
    """Multiply base scores by rating factor."""
    if not scores:
        return scores
    book_ids = [bid for bid, _ in scores]
    rating_factors = _fetch_rating_scores(book_ids)
    boosted: List[Tuple[int, float]] = []
    for book_id, base in scores:
        factor = rating_factors.get(book_id, 1.0)
        boosted.append((book_id, base * factor))
    # Re-normalize to [0,1]
    if not boosted:
        return scores
    max_score = max(s for _, s in boosted) or 1.0
    return [(bid, s / max_score) for bid, s in boosted]


def _apply_category_preference(
    customer_id: int,
    scores: List[Tuple[int, float]],
    customer_books: Dict[int, set],
) -> List[Tuple[int, float]]:
    """
    Slightly boost books that belong to categories the customer buys a lot.
    """
    if not scores or customer_id not in customer_books:
        return scores

    purchased_book_ids = list(customer_books[customer_id])
    cat_map = _fetch_book_categories(
        list({*purchased_book_ids, *[bid for bid, _ in scores]})
    )
    if not cat_map:
        return scores

    # Count categories in customer's history
    cat_counts: Dict[int, int] = defaultdict(int)
    for bid in purchased_book_ids:
        cat_id = cat_map.get(bid)
        if cat_id is not None:
            cat_counts[cat_id] += 1
    if not cat_counts:
        return scores

    max_count = max(cat_counts.values()) or 1
    boosted: List[Tuple[int, float]] = []
    for book_id, base in scores:
        cat_id = cat_map.get(book_id)
        if cat_id is None or cat_id not in cat_counts:
            boosted.append((book_id, base))
            continue
        pref = cat_counts[cat_id] / max_count  # 0–1
        factor = 1.0 + 0.2 * pref  # up to +20%
        boosted.append((book_id, base * factor))

    max_score = max(s for _, s in boosted) or 1.0
    return [(bid, s / max_score) for bid, s in boosted]


def _deep_learning_recommendations(
    customer_id: int, limit: int
) -> Optional[List[Tuple[int, float]]]:
    """
    Neural CF (model_behavior) over completed orders; None if no checkpoint
    or user/book out of vocabulary.
    """
    from . import model_behavior as mb

    purchased: Set[int] = set()
    for order in _fetch_customer_orders(customer_id):
        for item in order.get("items", []):
            purchased.add(item["book_id"])

    pool = max(limit * 5, 20)
    raw = mb.recommend_from_behavior_model(customer_id, purchased, pool)
    if not raw:
        return None

    max_score = max(s for _, s in raw) or 1.0
    normalized = [(book_id, s / max_score) for book_id, s in raw]

    all_orders = _fetch_all_orders()
    customer_books: dict = defaultdict(set)
    for order in all_orders:
        cid = order.get("customer_id")
        for item in order.get("items", []):
            customer_books[cid].add(item["book_id"])

    boosted = _apply_rating_boost(normalized)
    boosted = _apply_category_preference(customer_id, boosted, customer_books)
    boosted.sort(key=lambda x: x[1], reverse=True)
    return boosted[:limit]


def popularity_based(limit: int = 10) -> List[Tuple[int, float]]:
    """Return (book_id, score) tuples ranked by purchase frequency, boosted by rating."""
    orders = _fetch_all_orders()
    counts: dict = defaultdict(int)
    for order in orders:
        for item in order.get("items", []):
            counts[item["book_id"]] += item.get("quantity", 1)
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    if not ranked:
        return []
    max_count = ranked[0][1] or 1
    base_scores = [(book_id, count / max_count) for book_id, count in ranked]
    return _apply_rating_boost(base_scores)


def collaborative_filtering(customer_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    """User-based collaborative filtering using cosine similarity."""
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("numpy/sklearn not available; falling back to popularity.")
        return popularity_based(limit)

    # Build customer → set of purchased book_ids
    all_orders = _fetch_all_orders()
    customer_books: dict = defaultdict(set)
    for order in all_orders:
        cid = order.get("customer_id")
        for item in order.get("items", []):
            customer_books[cid].add(item["book_id"])

    if not customer_books:
        return popularity_based(limit)

    all_book_ids = sorted({b for books in customer_books.values() for b in books})
    if not all_book_ids:
        return popularity_based(limit)

    book_index = {b: i for i, b in enumerate(all_book_ids)}
    customer_ids = sorted(customer_books.keys())
    customer_index = {c: i for i, c in enumerate(customer_ids)}

    matrix = np.zeros((len(customer_ids), len(all_book_ids)), dtype=np.float32)
    for cid, books in customer_books.items():
        for book in books:
            matrix[customer_index[cid], book_index[book]] = 1.0

    if customer_id not in customer_index:
        return popularity_based(limit)

    target_vec = matrix[customer_index[customer_id]].reshape(1, -1)
    similarities = cosine_similarity(target_vec, matrix)[0]
    already_purchased = customer_books[customer_id]

    candidate_scores: dict = defaultdict(float)
    for i, sim in enumerate(similarities):
        if customer_ids[i] == customer_id or sim <= 0:
            continue
        for book_id in customer_books[customer_ids[i]]:
            if book_id not in already_purchased:
                candidate_scores[book_id] += sim

    if not candidate_scores:
        return popularity_based(limit)

    ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    if not ranked:
        return []

    max_score = ranked[0][1] or 1
    base_scores = [(book_id, score / max_score) for book_id, score in ranked]

    # 1) boost by book rating
    boosted = _apply_rating_boost(base_scores)
    # 2) boost by customer's preferred categories
    boosted = _apply_category_preference(customer_id, boosted, customer_books)
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


def item_based_similar(book_id: int, limit: int = 10) -> List[Tuple[int, float]]:
    """
    Simple item-based recommendation: books often bought together with `book_id`.
    """
    orders = _fetch_all_orders()
    co_counts: Dict[int, int] = defaultdict(int)
    for order in orders:
        items = [it["book_id"] for it in order.get("items", [])]
        if book_id not in items:
            continue
        for other in items:
            if other == book_id:
                continue
            co_counts[other] += 1

    if not co_counts:
        return popularity_based(limit)

    ranked = sorted(co_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    max_count = ranked[0][1] or 1
    base_scores = [(bid, c / max_count) for bid, c in ranked]
    # Boost by ratings as well
    return _apply_rating_boost(base_scores)
