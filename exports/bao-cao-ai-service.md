# BÁO CÁO: XÂY DỰNG CÁC MÔ HÌNH ĐỂ DỰ ĐOÁN VÀ PHÂN LOẠI HÀNH VI KHÁCH HÀNG

## 1. Mục tiêu và phạm vi

Báo cáo này mô tả các mô hình dự đoán/phân loại hành vi khách hàng đang được sử dụng thực tế trong project `microservice-bookstore`, dựa trên mã nguồn hiện có ở các service:

- `recommender-ai-service`
- `graph-rag-service`
- `rag-service`

Trọng tâm là:

1. Mô hình dự đoán sản phẩm khách có khả năng quan tâm/mua.
2. Cơ chế phân loại hành vi theo sự kiện (`view`, `click`, `add_to_cart`, `purchase`).
3. Cơ chế cá nhân hóa theo hồ sơ hành vi để phục vụ chatbot và gợi ý.

---

## 2. Dữ liệu hành vi đầu vào

### 2.1 Dữ liệu mua hàng (purchase behavior)

Nguồn chính từ `order-service`:

- `GET /api/orders/`
- `GET /internal/orders/customer/{customer_id}/history/`

Hệ thống chỉ dùng đơn hoàn tất: `PAID`, `SHIPPED`, `DELIVERED` để đảm bảo tín hiệu hành vi có chất lượng.

### 2.2 Dữ liệu tương tác (interaction behavior)

Trong `recommender-ai-service`, dữ liệu hành vi được lưu dưới dạng `BehaviorEvent` với các nhãn:

- `view`
- `click`
- `add_to_cart`

Frontend đã ghi các sự kiện này khi người dùng (role customer) xem sản phẩm, click card, thêm giỏ hàng.

### 2.3 Dữ liệu ngữ cảnh sản phẩm và phản hồi

- Category/product metadata từ `product-service` (bulk API).
- Rating summary từ `comment-rate-service` để tăng/giảm điểm gợi ý theo chất lượng sản phẩm.

---

## 3. Các mô hình dự đoán hành vi đã triển khai

### 3.1 Neural Collaborative Filtering (Behavior DL)

**Vị trí mã:** `recommender/model_behavior.py`

Đây là mô hình dự đoán chính khi có checkpoint:

- User embedding + item embedding.
- Ghép vector và đưa qua MLP nhiều tầng.
- Đầu ra affinity score (sigmoid) cho cặp `(customer, product)`.

#### Huấn luyện

- Positive sample: cặp user-item đã mua trong đơn hoàn tất.
- Negative sampling: item user chưa mua.
- Loss: `BCEWithLogitsLoss`.
- Optimizer: Adam.

#### Suy luận

- Với mỗi customer, model chấm điểm các item chưa mua.
- Trả về top-K sản phẩm có xác suất cao nhất.

=> Vai trò: dự đoán xu hướng mua/quan tâm cá nhân hóa ở mức sâu.

### 3.2 User-based Collaborative Filtering (Cosine)

**Vị trí mã:** `recommender/engine.py::collaborative_filtering`

Cách làm:

- Tạo ma trận nhị phân `customer x product` từ lịch sử mua.
- Tính cosine similarity giữa user mục tiêu và các user khác.
- Lấy sản phẩm từ các user tương tự mà user mục tiêu chưa mua.

=> Vai trò: fallback chất lượng cao khi DL model không khả dụng hoặc không bao phủ user.

### 3.3 Popularity-based fallback

**Vị trí mã:** `recommender/engine.py::popularity_based`

- Xếp hạng sản phẩm theo tần suất mua toàn cục.
- Dùng cho cold-start hoặc thiếu dữ liệu cộng tác.

=> Vai trò: bảo đảm hệ thống luôn có kết quả dự đoán, tránh rỗng output.

### 3.4 Item-based co-occurrence

**Vị trí mã:** `recommender/engine.py::item_based_similar`

- Đếm mức đồng xuất hiện sản phẩm trong cùng đơn.
- Trả về nhóm “mua kèm” / “có thể thích cùng”.

=> Vai trò: dự đoán hành vi kiểu “đã xem/mua X thì có xu hướng thích Y”.

---

## 4. Các tầng tăng cường điểm (re-ranking theo hành vi)

Sau khi có điểm từ model, hệ thống tăng cường theo tín hiệu hành vi thực tế:

1. **Rating boost**
   - Chuẩn hóa điểm sao và nhân hệ số lên score gợi ý.
2. **Category preference boost**
   - Phân tích danh mục user mua nhiều, tăng điểm cho candidate cùng danh mục.

=> Đây là lớp hậu xử lý giúp dự đoán gần hơn với sở thích thực tế của khách hàng.

---

## 5. Phân loại hành vi khách hàng trong project

Project hiện phân loại hành vi theo hai lớp:

### 5.1 Phân loại sự kiện (event-level classification)

Mỗi hành vi được gán nhãn rời rạc:

- `view`
- `click`
- `add_to_cart`
- `purchase` (suy ra từ order line items khi export/report)

Lớp nhãn này được dùng cho:

- phân tích funnel hành vi,
- xuất báo cáo CSV,
- tạo cạnh hành vi trong graph.

### 5.2 Phân loại hồ sơ sở thích (profile-level behavioral classification)

`graph-rag-service/graph_retriever.py` truy vấn và gom các đặc trưng hành vi theo customer:

- sản phẩm đã mua nhiều,
- sản phẩm đã xem/click,
- danh mục yêu thích,
- gợi ý từ nhóm khách tương tự.

Dù chưa phải classifier supervised kiểu XGBoost, đây là cơ chế phân loại hồ sơ hành vi đang chạy production để cá nhân hóa theo user.

---

## 6. Mô hình hóa hành vi bằng đồ thị và ứng dụng vào chatbot

### 6.1 Đồ thị hành vi Neo4j

`graph-rag-service` đồng bộ dữ liệu thành graph:

- Node: `Customer`, `Product`, `Category`
- Edge: `PURCHASED`, `VIEWED`, `CLICKED`, `ADDED_TO_CART`, `IN_CATEGORY`

### 6.2 Kết hợp với RAG

`rag-service` nhận `customer_id`, gọi graph context, rồi ghép vào prompt trong `rag_engine.py`:

- thông tin đã mua,
- đã xem/click,
- danh mục yêu thích,
- gợi ý từ khách tương tự.

Đồng thời dùng Hybrid Retrieval (BM25 + FAISS + RRF) trên tài liệu tri thức cửa hàng.

=> Kết quả: chatbot trả lời theo ngữ cảnh cá nhân, không chỉ trả lời chung chung.

---

## 7. Chính sách chọn mô hình khi serving

Hàm `get_recommendations(customer_id, limit)` chọn chiến lược theo thứ tự:

1. `behavior_dl` (NCF) nếu checkpoint và vocabulary hợp lệ.
2. `collaborative_filtering` nếu DL không dùng được.
3. `popularity` nếu tiếp tục thiếu dữ liệu.

Đây là policy nhiều tầng giúp hệ thống ổn định ở cả warm-start lẫn cold-start.

---

## 8. Chỉ số theo dõi hiệu quả hiện có

Trong `recommender/analytics.py`, project đã theo dõi:

- `recommendation_impressions`
- `recommendation_conversions`
- `recommendation_conversion_rate`
- tổng đơn / tổng item / phân bố mua theo category

Các chỉ số này là baseline tốt để đánh giá hiệu quả dự đoán hành vi theo thời gian.

---

## 9. Đánh giá mức độ đáp ứng đề tài

Với yêu cầu “xây dựng các mô hình để dự đoán và phân loại hành vi khách hàng”, project đã đáp ứng ở mức tốt:

- Có mô hình dự đoán rõ ràng: NCF + CF + popularity + item-based.
- Có phân loại hành vi theo event type.
- Có phân loại hồ sơ hành vi theo graph context.
- Có tích hợp trực tiếp vào trải nghiệm người dùng (recommendation + chatbot cá nhân hóa).

### Hạn chế

- Chưa có supervised classifier cho các nhãn kinh doanh (churn risk, high-value segment, intent score).
- Chưa có pipeline huấn luyện tự động định kỳ và A/B test chuẩn hóa.

### Hướng nâng cấp

1. Bổ sung mô hình phân khúc khách hàng (RFM + tree model).
2. Tạo offline evaluation (Precision@K, Recall@K, NDCG@K).
3. Kết hợp tín hiệu `view/click/add_to_cart` trực tiếp vào pipeline training DL (không chỉ dùng cho graph/prompt).

---

## 10. Kết luận

Hệ thống `microservice-bookstore` hiện đã xây dựng được kiến trúc mô hình hành vi đa tầng, gồm:

- **Prediction layer:** NCF, Collaborative Filtering, Popularity, Item-based.
- **Behavior classification layer:** event taxonomy + profile context.
- **Personalization layer:** Graph-enhanced RAG.

Kiến trúc này phù hợp với bài toán thương mại điện tử thực tế và có khả năng mở rộng lên các mô hình phân loại nâng cao trong các giai đoạn tiếp theo.
