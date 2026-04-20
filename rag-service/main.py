import logging
from typing import Optional

import requests as http_client
import uvicorn
from decouple import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_engine import HybridRAG

logger = logging.getLogger(__name__)

GRAPH_RAG_SERVICE_URL = config(
    "GRAPH_RAG_SERVICE_URL", default="http://graph-rag-service:8000"
)
_GRAPH_CONTEXT_TIMEOUT = 5  # seconds — fail fast; chat still works without context

app = FastAPI(title="RAG Chatbot Service - Microservice Bookstore")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Initializing Hybrid RAG Engine...")
rag_system = HybridRAG()
print("RAG Engine Initialization Complete.")


class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[int] = None  # None → anonymous / not logged in


class ChatResponse(BaseModel):
    reply: str
    personalized: bool = False


def _fetch_personal_context(customer_id: int) -> Optional[dict]:
    """Call graph-rag-service synchronously; return None on any failure."""
    try:
        url = f"{GRAPH_RAG_SERVICE_URL}/api/graph-rag/context/{customer_id}"
        resp = http_client.get(url, timeout=_GRAPH_CONTEXT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data if data.get("found") else None
    except Exception as exc:
        logger.warning("graph-rag context fetch failed (cid=%s): %s", customer_id, exc)
        return None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rag-service"}


@app.get("/admin/")
def admin_health_check():
    return {"status": "ok", "service": "rag-service"}


@app.post("/api/rag/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Personalized RAG chat.
    - If customer_id is provided and found in Neo4j, the reply is enriched with
      the customer's purchase history, viewed products, and favourite categories.
    - Falls back gracefully to generic knowledge-base chat when graph context is
      unavailable (anonymous user, Neo4j not synced, graph-rag down, etc.).
    """
    personal_context = None
    if request.customer_id:
        personal_context = _fetch_personal_context(request.customer_id)

    reply = rag_system.chat_with_context(
        request.message, personal_context=personal_context
    )
    return ChatResponse(reply=reply, personalized=personal_context is not None)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
