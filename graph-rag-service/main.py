"""Minimal HTTP API: health checks + trigger Neo4j graph sync from microservices."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph_builder import GraphBuilder

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
