import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_engine import HybridRAG

app = FastAPI(title="RAG Chatbot Service - Microservice Bookstore")

# Cấu hình CORS để cho phép Frontend (ví dụ React trên port 3000) truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Hệ thống RAG tự động khi chạy server
print("Initializing Hybrid RAG Engine...")
rag_system = HybridRAG()
print("RAG Engine Initialization Complete.")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.get("/health")
def health_check():
    """Endpoint dùng để gateway kiểm tra trạng thái."""
    return {"status": "ok", "service": "rag-service"}

@app.get("/admin/")
def admin_health_check():
    """Django style health check for gateway compatible ping."""
    return {"status": "ok", "service": "rag-service"}

@app.post("/api/rag/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """API chính để nhận câu hỏi và trả về câu trả lời."""
    try:
        reply = rag_system.chat(request.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Để khởi chạy khi dùng file run test trực tiếp thay vì Docker
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
