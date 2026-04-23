import os
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
import google.generativeai as genai
from decouple import config
import openai

# Lấy API KEY từ biến môi trường (Config qua docker-compose)
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
AI_PROVIDER = config('AI_PROVIDER', default='openai') # ưu tiên openai, fallback gemini

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
if OPENAI_API_KEY:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None

class HybridRAG:
    def __init__(self, data_path="data/knowledge.txt"):
        self.documents = []
        self.bm25_corpus = []
        self.bm25_index = None
        self.faiss_index = None
        self.embeddings = []
        
        self.EMBEDDING_MODEL = 'models/embedding-001'
        self.GENERATIVE_MODEL = 'gemini-2.5-flash'  # Use a recent performant model
        self.OPENAI_EMBEDDING_MODEL = 'text-embedding-3-small'
        self.OPENAI_GENERATIVE_MODEL = 'gpt-4o-mini'
        self.active_provider = self._resolve_provider(AI_PROVIDER)
        
        self.chunk_size = 400
        self.chunk_overlap = 50
        
        if self.active_provider in ('openai', 'gemini'):
            self.load_and_index(data_path)
        else:
            print("Warning: No API key found for OpenAI/Gemini. RAG engine will not initialize completely.")

    @staticmethod
    def _resolve_provider(preferred_provider: str) -> str | None:
        """Chọn provider theo thứ tự ưu tiên: OpenAI trước, sau đó Gemini."""
        preferred = (preferred_provider or '').strip().lower()

        if preferred == 'openai':
            if OPENAI_API_KEY:
                return 'openai'
            if GOOGLE_API_KEY:
                return 'gemini'
            return None

        if preferred == 'gemini':
            if GOOGLE_API_KEY:
                return 'gemini'
            if OPENAI_API_KEY:
                return 'openai'
            return None

        # Cấu hình không hợp lệ: vẫn ưu tiên OpenAI trước.
        if OPENAI_API_KEY:
            return 'openai'
        if GOOGLE_API_KEY:
            return 'gemini'
        return None
            
    def chunk_text(self, text, chunk_size, chunk_overlap):
        """Chia nhỏ văn bản thành các đoạn (chunks) có đoạn nối nhau (overlap)."""
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start+chunk_size])
            start += chunk_size - chunk_overlap
        return chunks

    def load_and_index(self, data_path):
        if not os.path.exists(data_path):
            print(f"Warning: Data file not found at {data_path}")
            return
            
        with open(data_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Chia cắt nội dung dựa trên delimiter do mình tự định nghĩa '==='
        blocks = content.split('===')
        raw_chunks = []
        for block in blocks:
            if block.strip():
                raw_chunks.extend(self.chunk_text(block.strip(), self.chunk_size, self.chunk_overlap))
                
        self.documents = raw_chunks
        print(f"Loaded {len(self.documents)} text chunks.")
        
        # 1. Khởi tạo Keyword Search (BM25)
        self.bm25_corpus = [doc.lower().split() for doc in self.documents]
        self.bm25_index = BM25Okapi(self.bm25_corpus)
        
        # 2. Khởi tạo Vector Search (FAISS)
        try:
            embedding_list = []
            if self.active_provider == 'openai' and openai_client:
                response = openai_client.embeddings.create(
                    input=self.documents,
                    model=self.OPENAI_EMBEDDING_MODEL
                )
                embedding_list = [item.embedding for item in response.data]
            else:
                embed_responses = genai.embed_content(
                    model=self.EMBEDDING_MODEL,
                    content=self.documents,
                    task_type="retrieval_document",
                )
                # Response của Google library có dạng: {'embedding': [[...], [...]]}
                embedding_list = embed_responses.get('embedding', embed_responses.get('embeddings', []))
            
            self.embeddings = np.array(embedding_list).astype('float32')
            
            if len(self.embeddings) > 0:
                dim = self.embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatL2(dim)
                self.faiss_index.add(self.embeddings)
                print(f"Indexed {len(self.documents)} chunks into FAISS vector database.")
        except Exception as e:
            print(f"Error building FAISS index (check your GOOGLE_API_KEY): {e}")

    def get_embedding(self, text):
        try:
            if self.active_provider == 'openai' and openai_client:
                response = openai_client.embeddings.create(
                    input=[text],
                    model=self.OPENAI_EMBEDDING_MODEL
                )
                emb = response.data[0].embedding
            else:
                response = genai.embed_content(
                    model=self.EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_query",
                )
                emb = response.get('embedding', response.get('embeddings', []))
            return np.array(emb).astype('float32').reshape(1, -1)
        except Exception as e:
            print(f"Error getting query embedding: {e}")
            return None

    def search_hybrid(self, query, top_k=3):
        if not self.documents:
            return []
            
        # 1. Tìm kiếm Vector (FAISS Similarity Search)
        faiss_scores = {}
        query_emb = self.get_embedding(query)
        if query_emb is not None and self.faiss_index is not None:
            # Tìm kiếm Top N xa nhất, L2 distance (càng nhỏ càng tốt)
            distances, indices = self.faiss_index.search(query_emb, len(self.documents))
            faiss_ranks = indices[0]
            # Chuyển đổi Rank thành Điểm số dựa trên thuật toán Reciprocal Rank Fusion (RRF)
            for rank, doc_idx in enumerate(faiss_ranks):
                faiss_scores[doc_idx] = 1.0 / (rank + 60)
        
        # 2. Tìm kiếm Từ khoá (BM25 Keyword Search)
        bm25_scores = {}
        tokenized_query = query.lower().split()
        doc_scores = self.bm25_index.get_scores(tokenized_query)
        # Chuyển đổi Điểm số thành Rank
        bm25_ranks = np.argsort(doc_scores)[::-1]
        for rank, doc_idx in enumerate(bm25_ranks):
            bm25_scores[doc_idx] = 1.0 / (rank + 60)
            
        # 3. Kết hợp Điểm số (Hybrid RRF)
        final_scores = {}
        for doc_idx in range(len(self.documents)):
            score = faiss_scores.get(doc_idx, 0) + bm25_scores.get(doc_idx, 0)
            final_scores[doc_idx] = score
            
        # Sắp xếp và lấy ra top K kết quả văn bản tốt nhất
        sorted_indices = sorted(final_scores.keys(), key=lambda x: final_scores[x], reverse=True)
        top_indices = sorted_indices[:top_k]
        
        results = [self.documents[idx] for idx in top_indices]
        return results

    @staticmethod
    def _build_personal_section(ctx: dict) -> str:
        """Chuyển personal context dict → đoạn văn bản tiếng Việt cho LLM."""
        if not ctx or not ctx.get("found"):
            return ""

        lines = []
        name = ctx.get("name") or "Khách hàng"
        lines.append(f"Tên khách hàng: {name}")

        purchased = ctx.get("purchased_products") or []
        if purchased:
            items = ", ".join(
                f"{p['title']} ({p.get('category', 'N/A')}, {p.get('times', 1)} lần)"
                for p in purchased[:6]
            )
            lines.append(f"Đã mua: {items}")

        viewed = ctx.get("viewed_products") or []
        if viewed:
            titles = ", ".join(v["title"] for v in viewed[:5])
            lines.append(f"Đã xem/click: {titles}")

        fav = ctx.get("favourite_categories") or []
        if fav:
            lines.append(f"Danh mục yêu thích: {', '.join(fav)}")

        collab = ctx.get("collaborative_suggestions") or []
        if collab:
            lines.append(f"Khách tương tự cũng mua: {', '.join(collab[:4])}")

        return "\n".join(lines)

    def chat(self, user_message: str):
        return self.chat_with_context(user_message, personal_context=None)

    def chat_with_context(self, user_message: str, personal_context: dict | None = None):
        if self.active_provider == 'gemini' and not GOOGLE_API_KEY:
            return "Xin lỗi, Server chưa được cấu hình GOOGLE_API_KEY. Quản trị viên vui lòng đặt biến trong file .env ở thư mục gốc project (xem .env.example)."
        if self.active_provider == 'openai' and not OPENAI_API_KEY:
            return "Xin lỗi, Server chưa được cấu hình OPENAI_API_KEY. Quản trị viên vui lòng đặt biến trong file .env ở thư mục gốc project."
        if self.active_provider is None:
            return "Xin lỗi, Server chưa được cấu hình API key cho OpenAI hoặc Gemini."

        # Lấy ngữ cảnh kiến thức tĩnh (Knowledge Base Retrieval)
        retrieved_contexts = self.search_hybrid(user_message, top_k=3)
        context_str = "\n\n".join([f"- {c}" for c in retrieved_contexts])

        # Xây dựng phần cá nhân hoá (nếu có)
        personal_section = self._build_personal_section(personal_context)
        if personal_section:
            personal_block = f"""--- THÔNG TIN CÁ NHÂN HOÁ KHÁCH HÀNG ---
{personal_section}

"""
            greeting_hint = (
                f"Hãy gọi tên khách hàng ({personal_context.get('name', '')}) "
                "và cá nhân hoá câu trả lời dựa trên lịch sử mua hàng / sở thích của họ khi phù hợp. "
            )
        else:
            personal_block = ""
            greeting_hint = ""

        prompt = f"""Bạn là một AI Assistant thân thiện có tên "Bookstore AI" làm việc tại cửa hàng "Microservice Bookstore".
{greeting_hint}Bạn được phép sử dụng cả thông tin cá nhân hoá lẫn tài liệu cửa hàng bên dưới để trả lời.
Nếu không có thông tin phù hợp, hãy phản hồi tế nhị và khuyên khách gọi Hotline 1900-1234.
Luôn trả lời ngắn gọn, súc tích bằng Tiếng Việt.

{personal_block}--- THÔNG TIN LẤY ĐƯỢC TỪ TÀI LIỆU CỬA HÀNG ---
{context_str}

---
Câu hỏi: {user_message}
Bot trả lời:"""

        try:
            if self.active_provider == 'openai' and openai_client:
                response = openai_client.chat.completions.create(
                    model=self.OPENAI_GENERATIVE_MODEL,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            else:
                model = genai.GenerativeModel(self.GENERATIVE_MODEL)
                response = model.generate_content(prompt)
                return response.text
        except Exception as e:
            return f"Xin lỗi, tôi đang gặp lỗi khi kết nối với AI ({str(e)}). Bạn có thể thử lại sau."
