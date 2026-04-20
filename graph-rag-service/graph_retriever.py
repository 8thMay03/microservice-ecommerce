"""
Personal context retrieval from Neo4j for RAG personalization.

Returns a structured dict describing what the customer has done so far:
  - name / email
  - purchased products (title, category, times)
  - viewed / clicked products
  - favourite categories (inferred from purchases)
  - collaborative hint: products bought by similar customers
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from decouple import config
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

NEO4J_URI = config("NEO4J_URI", default="bolt://localhost:7687")
NEO4J_USER = config("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = config("NEO4J_PASSWORD", default="neo4jpassword123")


class PersonalContextRetriever:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self) -> None:
        self.driver.close()

    def _query(self, cypher: str, **params) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run(cypher, **params)
                return [record.data() for record in result]
        except Exception as exc:
            logger.warning("Neo4j query failed: %s", exc)
            return []

    # ── individual sub-queries ────────────────────────────────────────────────

    def _customer_info(self, customer_id: int) -> Optional[Dict]:
        rows = self._query(
            "MATCH (c:Customer {id: $cid}) RETURN c.name AS name, c.email AS email",
            cid=customer_id,
        )
        return rows[0] if rows else None

    def _purchased_products(self, customer_id: int, limit: int = 10) -> List[Dict]:
        return self._query(
            """
            MATCH (c:Customer {id: $cid})-[r:PURCHASED]->(p:Product)
            OPTIONAL MATCH (p)-[:IN_CATEGORY]->(cat:Category)
            RETURN p.title AS title, p.brand AS brand,
                   p.price AS price, cat.name AS category,
                   r.times AS times
            ORDER BY r.times DESC
            LIMIT $limit
            """,
            cid=customer_id,
            limit=limit,
        )

    def _viewed_products(self, customer_id: int, limit: int = 8) -> List[Dict]:
        return self._query(
            """
            MATCH (c:Customer {id: $cid})-[r:VIEWED|CLICKED]->(p:Product)
            RETURN DISTINCT p.title AS title, p.brand AS brand,
                            p.price AS price
            LIMIT $limit
            """,
            cid=customer_id,
            limit=limit,
        )

    def _favourite_categories(self, customer_id: int, limit: int = 5) -> List[str]:
        rows = self._query(
            """
            MATCH (c:Customer {id: $cid})-[:PURCHASED]->(p:Product)-[:IN_CATEGORY]->(cat:Category)
            RETURN cat.name AS category, count(p) AS cnt
            ORDER BY cnt DESC
            LIMIT $limit
            """,
            cid=customer_id,
            limit=limit,
        )
        return [r["category"] for r in rows if r.get("category")]

    def _collaborative_hints(self, customer_id: int, limit: int = 5) -> List[str]:
        """Products bought by customers who share ≥1 purchase with this customer."""
        rows = self._query(
            """
            MATCH (c:Customer {id: $cid})-[:PURCHASED]->(p:Product)
                  <-[:PURCHASED]-(other:Customer)-[:PURCHASED]->(rec:Product)
            WHERE NOT (c)-[:PURCHASED]->(rec)
            RETURN rec.title AS title, count(other) AS support
            ORDER BY support DESC
            LIMIT $limit
            """,
            cid=customer_id,
            limit=limit,
        )
        return [r["title"] for r in rows if r.get("title")]

    # ── public API ────────────────────────────────────────────────────────────

    def get_context(self, customer_id: int) -> Dict[str, Any]:
        """Return a serialisable dict with all personalisation signals."""
        info = self._customer_info(customer_id)
        if info is None:
            return {"found": False, "customer_id": customer_id}

        purchased = self._purchased_products(customer_id)
        viewed = self._viewed_products(customer_id)
        fav_cats = self._favourite_categories(customer_id)
        collab = self._collaborative_hints(customer_id)

        return {
            "found": True,
            "customer_id": customer_id,
            "name": info.get("name", ""),
            "email": info.get("email", ""),
            "purchased_products": purchased,
            "viewed_products": viewed,
            "favourite_categories": fav_cats,
            "collaborative_suggestions": collab,
        }
