import os
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
import google.generativeai as genai
from decouple import config

# Lấy API KEY từ biến môi trường (Config qua docker-compose)
GOOGLE_API_KEY = config('GOOGLE_API_KEY', default='')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class HybridRAG:
    def __init__(self, data_path="data/sample_knowledge.txt"):
        self.documents = []
        self.bm25_corpus = []
        self.bm25_index = None
        self.faiss_index = None
        self.embeddings = []
        
        self.EMBEDDING_MODEL = 'models/embedding-001'
        self.GENERATIVE_MODEL = 'gemini-2.5-flash'  # Use a recent performant model
        
        self.chunk_size = 400
        self.chunk_overlap = 50
        
        if GOOGLE_API_KEY:
            self.load_and_index(data_path)
        else:
            print("Warning: GOOGLE_API_KEY is not set. RAG engine will not initialize completely.")
            
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

    def chat(self, user_message: str):
        if not GOOGLE_API_KEY:
            return "Xin lỗi, Server chưa được cấu hình GOOGLE_API_KEY. Quản trị viên vui lòng thêm API Key vào hệ thống (docker-compose.yml)."
            
        # Lấy ngữ cảnh (Context Retrieval)
        retrieved_contexts = self.search_hybrid(user_message, top_k=3)
        context_str = "\n\n".join([f"- {c}" for c in retrieved_contexts])
        
        # Xây dựng Prompt (Augmented Generation)
        prompt = f"""Bạn là một AI Assistant thân thiện có tên "Bookstore AI" làm việc tại cửa hàng "Microservice Bookstore".
Bạn có nhiệm vụ dùng **duy nhất** các thông tin dưới đây để trả lời câu hỏi của khách hàng.
Nếu thông tin dưới đây không có lời giải, xin hãy phản hồi tế nhị rằng bạn không có thông tin và khuyên khách hàng gọi điện qua số Hotline 1900-1234.
Luôn trả lời ngắn gọn, súc tích bằng Tiếng Việt.

--- THÔNG TIN LẤY ĐƯỢC TỪ CƠ SỞ TÀI LIỆU CỦA CỬA HÀNG ---
{context_str}

---
Câu hỏi của khách hàng: {user_message}
Bot trả lời:"""

        try:
            model = genai.GenerativeModel(self.GENERATIVE_MODEL)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Xin lỗi, tôi đang gặp lỗi khi kết nối với AI ({str(e)}). Bạn có thể thử lại sau."
