"""
Neo4j ETL: loads full category tree (all rows from catalog DB), then links products.

Order of operations
-------------------
1. Flat list of categories (internal API, or flattened nested public API)
2. MERGE every :Category node
3. MERGE (:Category)-[:PARENT_OF]->(:Category) for subcategories
4. MERGE :Product and (:Product)-[:IN_CATEGORY]->(:Category) when category_id matches

Environment (docker-compose / local)
------------------------------------
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
  CATALOG_SERVICE_URL, PRODUCT_SERVICE_URL
  Optional: CUSTOMER_SERVICE_URL, ORDER_SERVICE_URL, RECOMMENDER_SERVICE_URL
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests
from decouple import config
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

CATALOG_SERVICE_URL = config("CATALOG_SERVICE_URL", default="http://catalog-service:8000")
PRODUCT_SERVICE_URL = config("PRODUCT_SERVICE_URL", default="http://product-service:8000")
CUSTOMER_SERVICE_URL = config("CUSTOMER_SERVICE_URL", default="http://customer-service:8000")
ORDER_SERVICE_URL = config("ORDER_SERVICE_URL", default="http://order-service:8000")
RECOMMENDER_SERVICE_URL = config(
    "RECOMMENDER_SERVICE_URL", default="http://recommender-ai-service:8000"
)

NEO4J_URI = config("NEO4J_URI", default="bolt://localhost:7687")
NEO4J_USER = config("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = config("NEO4J_PASSWORD", default="neo4jpassword123")

_TIMEOUT = 15
COMPLETED_STATUSES = frozenset({"PAID", "SHIPPED", "DELIVERED"})


def _get(url: str, params: Optional[dict] = None) -> Optional[Any]:
    try:
        r = requests.get(url, params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def _flatten_nested_categories(nodes: List[dict]) -> List[Dict[str, Any]]:
    """Turn nested GET /api/catalog/categories/ payload into flat rows."""
    rows: List[Dict[str, Any]] = []

    def walk(c: dict, parent_id: Optional[int]) -> None:
        cid = c.get("id")
        if cid is None:
            return
        cid = int(cid)
        rows.append(
            {
                "id": cid,
                "name": c.get("name") or "",
                "slug": c.get("slug") or "",
                "parent": parent_id,
            }
        )
        for ch in c.get("children") or []:
            if isinstance(ch, dict):
                walk(ch, cid)

    for root in nodes or []:
        if isinstance(root, dict):
            walk(root, None)
    return rows


def fetch_categories_flat() -> List[Dict[str, Any]]:
    """
    Prefer internal flat list (all categories in one response).
    Fallback: public nested tree → flatten in Python.
    """
    internal = _get(f"{CATALOG_SERVICE_URL}/internal/catalog/categories/all/")
    if isinstance(internal, list) and internal:
        out = []
        for c in internal:
            try:
                pid = c.get("parent_id")
                out.append(
                    {
                        "id": int(c["id"]),
                        "name": c.get("name") or "",
                        "slug": c.get("slug") or "",
                        "parent": int(pid) if pid is not None else None,
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        logger.info("categories: loaded %s rows from internal flat API", len(out))
        return out

    nested = _get(f"{CATALOG_SERVICE_URL}/api/catalog/categories/")
    if not isinstance(nested, list):
        logger.warning("categories: unexpected public API shape")
        return []
    flat = _flatten_nested_categories(nested)
    logger.info("categories: flattened %s rows from nested public API", len(flat))
    return flat


def fetch_all_products() -> List[dict]:
    all_rows: List[dict] = []
    page = 1
    while True:
        data = _get(
            f"{PRODUCT_SERVICE_URL}/api/products/",
            params={"page": page, "page_size": 100},
        )
        if not isinstance(data, dict):
            break
        chunk = data.get("results") or []
        if not chunk:
            break
        all_rows.extend(chunk)
        total = int(data.get("total") or 0)
        if len(all_rows) >= total or len(chunk) < 100:
            break
        page += 1
    logger.info("products: loaded %s rows", len(all_rows))
    return all_rows


def fetch_customers() -> List[dict]:
    data = _get(f"{CUSTOMER_SERVICE_URL}/api/customers/")
    if not isinstance(data, list):
        return []
    return data


def fetch_orders_completed() -> List[dict]:
    data = _get(f"{ORDER_SERVICE_URL}/api/orders/")
    if not isinstance(data, list):
        return []
    return [o for o in data if o.get("status") in COMPLETED_STATUSES]


def fetch_behavior_events() -> List[dict]:
    data = _get(
        f"{RECOMMENDER_SERVICE_URL}/internal/recommender/behavior-events/"
    )
    if not isinstance(data, list):
        return []
    return data


class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self) -> None:
        self.driver.close()

    def _run(self, cypher: str, **params) -> None:
        with self.driver.session() as session:
            session.run(cypher, **params)

    def setup_schema(self) -> None:
        stmts = [
            "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT category_id IF NOT EXISTS FOR (x:Category) REQUIRE x.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for stmt in stmts:
                try:
                    session.run(stmt)
                except Exception as exc:
                    logger.debug("constraint: %s", exc)

    def upsert_categories(self, categories: List[Dict[str, Any]]) -> None:
        """MERGE all category nodes (roots + every subcategory)."""
        if not categories:
            return
        self._run(
            """
            UNWIND $rows AS row
            MERGE (c:Category {id: row.id})
            SET c.name = row.name, c.slug = row.slug
            """,
            rows=categories,
        )
        parent_rows = [
            {"child_id": c["id"], "parent_id": c["parent"]}
            for c in categories
            if c.get("parent") is not None
        ]
        if parent_rows:
            self._run(
                """
                UNWIND $rows AS row
                MATCH (child:Category {id: row.child_id})
                MATCH (parent:Category {id: row.parent_id})
                MERGE (parent)-[:PARENT_OF]->(child)
                """,
                rows=parent_rows,
            )
        logger.info("upserted %d categories (+ %d parent edges)", len(categories), len(parent_rows))

    def upsert_products(self, products: List[dict]) -> None:
        rows = []
        for p in products:
            if p.get("id") is None:
                continue
            cid = p.get("category_id")
            rows.append(
                {
                    "id": int(p["id"]),
                    "title": p.get("title") or "",
                    "brand": p.get("brand") or "",
                    "price": float(p.get("price") or 0),
                    "product_type": p.get("product_type") or "",
                    "sku": p.get("sku") or "",
                    "description": (p.get("description") or "")[:4000],
                    "category_id": int(cid) if cid is not None else None,
                }
            )
        if not rows:
            return
        self._run(
            """
            UNWIND $rows AS row
            MERGE (p:Product {id: row.id})
            SET p.title = row.title,
                p.brand = row.brand,
                p.price = row.price,
                p.product_type = row.product_type,
                p.sku = row.sku,
                p.description = row.description
            WITH p, row
            WHERE row.category_id IS NOT NULL
            MATCH (cat:Category {id: row.category_id})
            MERGE (p)-[:IN_CATEGORY]->(cat)
            """,
            rows=rows,
        )
        logger.info("upserted %d products with IN_CATEGORY where category exists", len(rows))

    def upsert_customers(self, customers: List[dict]) -> None:
        rows = []
        for c in customers:
            if c.get("id") is None:
                continue
            rows.append(
                {
                    "id": int(c["id"]),
                    "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                    "email": c.get("email") or "",
                }
            )
        if not rows:
            return
        self._run(
            """
            UNWIND $rows AS row
            MERGE (c:Customer {id: row.id})
            SET c.name = row.name, c.email = row.email
            """,
            rows=rows,
        )

    def upsert_purchases(self, orders: List[dict]) -> None:
        from collections import defaultdict

        counts: Dict[tuple, int] = defaultdict(int)
        for o in orders:
            cid = o.get("customer_id")
            if cid is None:
                continue
            for it in o.get("items") or []:
                pid = it.get("product_id")
                if pid is not None:
                    counts[(int(cid), int(pid))] += 1
        rows = [{"cid": a, "pid": b, "times": t} for (a, b), t in counts.items()]
        if not rows:
            return
        self._run(
            """
            UNWIND $rows AS row
            MATCH (c:Customer {id: row.cid})
            MATCH (p:Product {id: row.pid})
            MERGE (c)-[r:PURCHASED]->(p)
            SET r.times = row.times
            """,
            rows=rows,
        )

    def upsert_behavior(self, events: List[dict]) -> None:
        from collections import defaultdict

        rel_map = {
            "view": "VIEWED",
            "click": "CLICKED",
            "add_to_cart": "ADDED_TO_CART",
        }
        counts: Dict[tuple, int] = defaultdict(int)
        for ev in events:
            try:
                key = (int(ev["customer_id"]), int(ev["product_id"]), str(ev.get("event_type", "")).lower())
            except (KeyError, TypeError, ValueError):
                continue
            if key[2] not in rel_map:
                continue
            counts[key] += 1
        for et, rel in rel_map.items():
            rows = [
                {"cid": k[0], "pid": k[1], "count": v}
                for k, v in counts.items()
                if k[2] == et
            ]
            if not rows:
                continue
            self._run(
                f"""
                UNWIND $rows AS row
                MATCH (c:Customer {{id: row.cid}})
                MATCH (p:Product {{id: row.pid}})
                MERGE (c)-[r:{rel}]->(p)
                SET r.count = row.count
                """,
                rows=rows,
            )

    def full_sync(self) -> Dict[str, int]:
        self.setup_schema()
        categories = fetch_categories_flat()
        products = fetch_all_products()
        customers = fetch_customers()
        orders = fetch_orders_completed()
        events = fetch_behavior_events()

        # Categories must exist before product IN_CATEGORY edges.
        self.upsert_categories(categories)
        self.upsert_products(products)
        self.upsert_customers(customers)
        self.upsert_purchases(orders)
        self.upsert_behavior(events)

        summary = {
            "categories": len(categories),
            "products": len(products),
            "customers": len(customers),
            "orders": len(orders),
            "events": len(events),
        }
        logger.info("full_sync done: %s", summary)
        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    b = GraphBuilder()
    try:
        print(b.full_sync())
    finally:
        b.close()
