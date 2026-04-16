

## Đề xuất phân công lại cho 4 người

### Người 1 - RAG + Knowledge Base
Phần nặng nhất về nội dung, đúng như bạn đã nghĩ.

- Bổ sung `knowledge.txt`: thêm 20+ đầu sách với tóm tắt, tác giả, cảm xúc, thể loại
- Tinh chỉnh prompt trong `rag_engine.py` để chatbot trả lời hay hơn
- Test các câu hỏi khó: "sách buồn như Rừng Na Uy", "sách cho người mới học đầu tư"
- Báo cáo: giải thích RAG flow, Hybrid Search (FAISS + BM25), demo screenshot

---

### Người 2 - NCF + Recommendation
- Seed dữ liệu order mẫu vào DB (viết script Python)
- Train model → tạo `behavior_model.pt`
- Verify 3 tầng fallback hoạt động đúng: NCF → CF → Popularity
- Thêm endpoint train model thủ công `/api/recommendations/train/` để demo live
- Báo cáo: giải thích NCF architecture, so sánh 3 chiến lược, biểu đồ loss khi train

---

### Người 3 - Semantic Search + Content Automation
Gộp 2 tính năng lại cho đủ việc.

- Semantic Search: embed query bằng Google API → tìm sách theo ý định thay vì keyword
- Content Automation: thêm endpoint `/api/books/<id>/summary/` dùng Gemini tự động tóm tắt sách khi manager thêm sách mới
- Cả 2 đều dùng chung `GOOGLE_API_KEY` đã có sẵn, không cần train gì
- Báo cáo: so sánh keyword search vs semantic search bằng ví dụ thực tế

---

### Người 4 - Observability + Tích hợp tổng thể + deploy
Bạn làm phần này như đã nói.

- Thêm Prometheus + Grafana + Loki + Promtail vào `docker-compose.yml`
- Tạo file config `monitoring/prometheus.yml` và `monitoring/promtail.yml`
- Thêm `django-prometheus` vào Gateway để expose `/metrics`
- Đảm bảo `docker compose up` chạy clean, test end-to-end toàn bộ luồng AI
- Báo cáo: giải thích observability stack, screenshot Grafana dashboard, Loki logs

---

