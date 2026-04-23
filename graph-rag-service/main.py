"""Minimal HTTP API: health checks + trigger Neo4j graph sync from microservices."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from graph_builder import GraphBuilder
from graph_retriever import PersonalContextRetriever

app = FastAPI(title="Graph RAG / Neo4j sync", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "graph-rag-service"}


@app.get("/admin/")
def admin_health():
    return {"status": "ok", "service": "graph-rag-service"}


class SyncResponse(BaseModel):
    status: str
    summary: dict


@app.post("/api/graph-rag/sync", response_model=SyncResponse)
def sync_graph():
    """Pull catalog / products / customers / orders (+ events if API exists) into Neo4j."""
    builder = GraphBuilder()
    try:
        summary = builder.full_sync()
        return SyncResponse(status="ok", summary=summary)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        builder.close()


@app.get("/api/graph-rag/context/{customer_id}")
def get_customer_context(customer_id: int) -> Dict[str, Any]:
    """
    Return personalisation signals for a given customer from Neo4j.
    Used by rag-service to enrich the LLM prompt before answering.
    """
    retriever = PersonalContextRetriever()
    try:
        ctx = retriever.get_context(customer_id)
        return ctx
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        retriever.close()
