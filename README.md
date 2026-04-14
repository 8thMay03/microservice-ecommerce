# Microservice BookStore

Hệ thống bookstore theo kiến trúc microservice, chạy bằng Docker Compose, gồm:
- `frontend` (React + Vite, serve qua Nginx)
- `api-gateway` (Django DRF reverse proxy)
- 12 backend services độc lập (mỗi service sở hữu DB riêng, trừ `rag-service`)

## 1) Tổng quan kiến trúc

```text
Client (Browser)
  -> Frontend: http://localhost:3000
  -> API Gateway: http://localhost:8000
       /api/<service>/<path>
       |-> customer-service
       |-> product-service
       |-> catalog-service
       |-> cart-service
       |-> order-service
       |-> pay-service
       |-> ship-service
       |-> comment-rate-service
       |-> recommender-ai-service
       |-> staff-service
       |-> manager-service
       |-> rag-service
```

Gateway forward request theo rule:
- Client gọi: `/api/<service>/<path>`
- Gateway forward tới: `<SERVICE_URL>/api/<service>/<path>`

---

## 2) Danh sách services trong hệ thống

### Service công khai cổng ra host

| Service | Port host | Mô tả |
|---|---:|---|
| `frontend` | `3000` | UI người dùng |
| `api-gateway` | `8000` | API entrypoint duy nhất |

### Service nội bộ (chạy trong Docker network)

| Service | Vai trò chính | DB riêng |
|---|---|---|
| `customer-service` | Quản lý khách hàng, auth khách hàng | `customer-db` |
| `product-service` | Sản phẩm + tồn kho | `product-db` |
| `catalog-service` | Danh mục sách | `catalog-db` |
| `cart-service` | Giỏ hàng | `cart-db` |
| `order-service` | Đơn hàng, điều phối payment + shipment | `order-db` |
| `pay-service` | Thanh toán | `pay-db` |
| `ship-service` | Vận chuyển, tracking | `ship-db` |
| `comment-rate-service` | Đánh giá + bình luận | `comment-rate-db` |
| `recommender-ai-service` | Gợi ý sách (behavior + rating signal) | `recommender-db` |
| `staff-service` | Nhân viên, nghiệp vụ kho | `staff-db` |
| `manager-service` | Quản trị, báo cáo tổng hợp | `manager-db` |
| `rag-service` | Chat RAG tư vấn sách | Không dùng PostgreSQL riêng |

---

## 3) Luồng nghiệp vụ chính

- **Đăng ký khách hàng**: `customer-service` có thể khởi tạo cart mặc định qua `cart-service`.
- **Tạo đơn hàng**: `order-service` gọi `cart-service` lấy item, gọi `pay-service` xử lý thanh toán, gọi `ship-service` tạo vận chuyển, sau đó clear cart.
- **Gợi ý sản phẩm**: `recommender-ai-service` lấy lịch sử mua từ `order-service`, kết hợp tín hiệu rating từ `comment-rate-service`.
- **RAG chat**: Frontend gọi `api-gateway` tới `/api/rag/chat` để nhận trả lời từ `rag-service`.

---

## 4) Quick Start

### Yêu cầu

- Docker Desktop (Docker + Compose v2)
- (Tuỳ chọn) Python 3.10+ để chạy script seed ngoài container

### Chạy toàn bộ hệ thống

```bash
docker compose up --build
```

Sau khi chạy:
- Frontend: `http://localhost:3000`
- API Gateway: `http://localhost:8000`
- Health check: `http://localhost:8000/health/`

### Dừng hệ thống

```bash
docker compose down
```

Xoá luôn volume DB:

```bash
docker compose down -v
```

---

## 5) Seed dữ liệu mẫu

Từ thư mục gốc project:

```bash
python scripts/seed_data.py
```

Script sẽ tạo:
- 7 categories
- 10 products mẫu
- tài khoản admin/staff
- 10 customer mẫu

Tham khảo thêm: `scripts/README.md`

---

## 6) API entrypoint (qua gateway)

Tất cả API đi qua gateway `http://localhost:8000` với format:

```text
/api/<service>/<path>
```

Một số nhóm endpoint thường dùng:

| Nhóm | Prefix |
|---|---|
| Customers | `/api/customers/` |
| Products | `/api/products/` |
| Catalog | `/api/catalog/` |
| Cart | `/api/cart/` |
| Orders | `/api/orders/` |
| Payments | `/api/payments/` |
| Shipments | `/api/shipments/` |
| Reviews | `/api/reviews/` |
| Recommendations | `/api/recommendations/` |
| Staff | `/api/staff/` |
| Managers | `/api/managers/` |
| RAG Chat | `/api/rag/chat` |

Ví dụ health:

```bash
curl http://localhost:8000/health/
```

Ví dụ chat RAG:

```bash
curl -X POST http://localhost:8000/api/rag/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Gợi ý cho tôi vài sách clean architecture\"}"
```

---

## 7) Cấu trúc thư mục

```text
microservice-bookstore/
├── docker-compose.yml
├── README.md
├── frontend/
├── api-gateway/
├── customer-service/
├── product-service/
├── catalog-service/
├── cart-service/
├── order-service/
├── pay-service/
├── ship-service/
├── comment-rate-service/
├── recommender-ai-service/
├── staff-service/
├── manager-service/
├── rag-service/
└── scripts/
```

---

## 8) Biến môi trường quan trọng

Phần lớn service sử dụng:
- `DEBUG`
- `SECRET_KEY`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `*_SERVICE_URL` để gọi service khác

Riêng `rag-service` cần:
- `GOOGLE_API_KEY`

Khuyến nghị:
- Không hardcode key thật trong `docker-compose.yml`.
- Dùng `.env` hoặc secret manager ở môi trường production.

---

## 9) Troubleshooting nhanh

- `gateway` báo `503`:
  - Kiểm tra service đích đã up chưa: `docker compose ps`
  - Xem log: `docker compose logs -f api-gateway <service-name>`
- Frontend không gọi được API:
  - Kiểm tra gateway đang nghe cổng `8000`
  - Kiểm tra prefix API trên frontend là `/api/...`
- DB migration lỗi:
  - Kiểm tra container DB tương ứng đã healthy
  - Chạy lại `docker compose up --build`

---

## 10) Production checklist (rút gọn)

- Tắt debug (`DEBUG=False`)
- Thay toàn bộ secret/key mặc định
- Giới hạn CORS theo domain cụ thể
- Thêm auth nội bộ service-to-service
- Bổ sung logging + tracing tập trung
- Thiết lập CI/CD + backup DB

# Microservice BookStore

A production-ready, fully Dockerized BookStore system built with **Django REST Framework**, following clean microservice architecture principles. Each service owns its data, communicates over HTTP REST, and is deployed as an independent container.

---

## Architecture Diagram

```
                        ┌─────────────────────────────┐
                        │         CLIENT / Browser     │
                        └──────────────┬──────────────┘
                                       │ HTTP :8000
                        ┌──────────────▼──────────────┐
                        │         API  GATEWAY         │
                        │   /api/<service>/<path>      │
                        │   Reverse proxy (requests)   │
                        └──┬────┬────┬────┬────┬───┬──┘
                           │    │    │    │    │   │
          ┌────────────────┘    │    │    │    │   └─────────────────┐
          │         ┌───────────┘    │    │    └──────────┐          │
          ▼         ▼                ▼    ▼               ▼          ▼
 ┌──────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐
 │  customer-   │ │   book-    │ │ catalog- │ │    cart-     │ │  order-  │
 │  service     │ │  service   │ │ service  │ │   service    │ │ service  │
 │  :8001       │ │  :8002     │ │  :8003   │ │   :8004      │ │  :8005   │
 └──────┬───────┘ └─────┬──────┘ └────┬─────┘ └──────┬───────┘ └────┬─────┘
        │               │             │               │               │
 ┌──────▼──┐     ┌──────▼──┐   ┌─────▼──┐    ┌──────▼──┐    ┌──────▼──┐
 │customer │     │  book   │   │catalog │    │  cart   │    │  order  │
 │   DB    │     │   DB    │   │   DB   │    │   DB    │    │   DB    │
 └─────────┘     └─────────┘   └────────┘    └─────────┘    └─────────┘

          ┌────────────┐ ┌──────────────┐ ┌───────────────────┐
          │   pay-     │ │    ship-     │ │  comment-rate-    │
          │  service   │ │   service   │ │     service       │
          │  :8006     │ │   :8007     │ │     :8008         │
          └─────┬──────┘ └──────┬───────┘ └────────┬──────────┘
                │               │                  │
          ┌─────▼──┐    ┌───────▼──┐       ┌───────▼──┐
          │  pay   │    │  ship    │       │comment   │
          │   DB   │    │   DB     │       │  rate DB │
          └────────┘    └──────────┘       └──────────┘

          ┌──────────────────┐ ┌──────────────┐ ┌───────────────┐
          │ recommender-ai-  │ │    staff-    │ │   manager-   │
          │    service       │ │   service    │ │   service    │
          │    :8009         │ │   :8010      │ │   :8011      │
          └────────┬─────────┘ └──────┬───────┘ └──────┬───────┘
                   │                  │                 │
          ┌────────▼──┐       ┌───────▼──┐     ┌───────▼──┐
          │recommender│       │  staff   │     │ manager  │
          │    DB     │       │   DB     │     │   DB     │
          └───────────┘       └──────────┘     └──────────┘
```

---

## Inter-Service Communication

```
Customer Registration:
  customer-service ──POST──▶ cart-service/internal/carts/create/

Create Order:
  order-service ──GET──▶  cart-service/internal/carts/{id}/
  order-service ──POST──▶ pay-service/internal/payments/process/
  order-service ──POST──▶ ship-service/internal/shipments/create/
  order-service ──DELETE──▶ cart-service/api/cart/{id}/clear/

Recommendations:
  recommender-ai-service ──GET──▶ order-service/internal/orders/customer/{id}/history/
  recommender-ai-service ──POST──▶ product-service/internal/products/bulk/

Manager Reports:
  manager-service ──GET──▶ order-service/api/orders/
  manager-service ──GET──▶ staff-service/internal/staff/
  manager-service ──GET──▶ customer-service/internal/customers/{id}/

Staff Inventory:
  staff-service ──PATCH──▶ product-service/api/products/{id}/inventory/
```

---

## Database Schema

### customer-service
```
customers
  id           BIGSERIAL PK
  email        VARCHAR UNIQUE
  password     VARCHAR (hashed)
  first_name   VARCHAR
  last_name    VARCHAR
  phone        VARCHAR
  address      TEXT
  is_active    BOOLEAN
  created_at   TIMESTAMP
  updated_at   TIMESTAMP
```

### product-service
```
products
  id               BIGSERIAL PK
  title            VARCHAR
  author           VARCHAR
  isbn             VARCHAR(13) UNIQUE
  description      TEXT
  price            DECIMAL(10,2)
  cover_image      VARCHAR (URL)
  category_id      INT  (FK → catalog-service)
  published_date   DATE
  language         VARCHAR
  pages            INT
  is_active        BOOLEAN
  created_at       TIMESTAMP

product_inventory
  id                BIGSERIAL PK
  product_id        INT UNIQUE FK → products
  stock_quantity    INT
  warehouse_location VARCHAR
  updated_at        TIMESTAMP
```

### catalog-service
```
categories
  id          BIGSERIAL PK
  name        VARCHAR UNIQUE
  slug        VARCHAR UNIQUE
  description TEXT
  parent_id   INT FK → categories (self-ref)
  created_at  TIMESTAMP
```

### cart-service
```
carts
  id          BIGSERIAL PK
  customer_id INT UNIQUE  (FK → customer-service)
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

cart_items
  id          BIGSERIAL PK
  cart_id     INT FK → carts
  product_id  INT  (FK → product-service)
  quantity    INT
  unit_price  DECIMAL(10,2)
  added_at    TIMESTAMP
  UNIQUE(cart_id, product_id)
```

### order-service
```
orders
  id               BIGSERIAL PK
  customer_id      INT  (FK → customer-service)
  status           VARCHAR  [PENDING|CONFIRMED|PAID|SHIPPED|DELIVERED|CANCELLED|REFUNDED]
  total_amount     DECIMAL(12,2)
  shipping_address TEXT
  payment_method   VARCHAR
  created_at       TIMESTAMP
  updated_at       TIMESTAMP

order_items
  id          BIGSERIAL PK
  order_id    INT FK → orders
  product_id  INT  (FK → product-service)
  product_title  VARCHAR
  quantity    INT
  unit_price  DECIMAL(10,2)
```

### pay-service
```
payments
  id             BIGSERIAL PK
  order_id       INT UNIQUE  (FK → order-service)
  customer_id    INT  (FK → customer-service)
  amount         DECIMAL(12,2)
  status         VARCHAR  [PENDING|COMPLETED|FAILED|REFUNDED]
  method         VARCHAR  [CREDIT_CARD|DEBIT_CARD|PAYPAL|BANK_TRANSFER]
  transaction_id UUID UNIQUE
  created_at     TIMESTAMP
  updated_at     TIMESTAMP
```

### ship-service
```
shipments
  id                BIGSERIAL PK
  order_id          INT UNIQUE  (FK → order-service)
  customer_id       INT  (FK → customer-service)
  shipping_address  TEXT
  status            VARCHAR  [PENDING|PROCESSING|SHIPPED|IN_TRANSIT|DELIVERED|RETURNED]
  tracking_number   UUID UNIQUE
  carrier           VARCHAR
  estimated_delivery DATE
  created_at        TIMESTAMP
  updated_at        TIMESTAMP
```

### comment-rate-service
```
ratings
  id          BIGSERIAL PK
  product_id  INT  (FK → product-service)
  customer_id INT  (FK → customer-service)
  score       SMALLINT  (1-5)
  created_at  TIMESTAMP
  updated_at  TIMESTAMP
  UNIQUE(product_id, customer_id)

comments
  id          BIGSERIAL PK
  product_id  INT  (FK → product-service)
  customer_id INT  (FK → customer-service)
  content     TEXT
  is_approved BOOLEAN
  created_at  TIMESTAMP
```

### recommender-ai-service
```
recommendation_cache
  id          BIGSERIAL PK
  customer_id INT
  product_id  INT
  score       FLOAT
  strategy    VARCHAR
  created_at  TIMESTAMP
  UNIQUE(customer_id, product_id)
```

### staff-service
```
staff_members
  id         BIGSERIAL PK
  email      VARCHAR UNIQUE
  password   VARCHAR (hashed)
  first_name VARCHAR
  last_name  VARCHAR
  role       VARCHAR  [WAREHOUSE|SALES|SUPPORT|MANAGER]
  is_active  BOOLEAN
  is_admin   BOOLEAN
  created_at TIMESTAMP
  updated_at TIMESTAMP
```

### manager-service
```
managers
  id         BIGSERIAL PK
  email      VARCHAR UNIQUE
  password   VARCHAR (hashed)
  first_name VARCHAR
  last_name  VARCHAR
  is_active  BOOLEAN
  created_at TIMESTAMP
```

---

## REST API Reference

All routes below are called through the **API Gateway** at `http://localhost:8000`.

### Customer Service  `/api/customers/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/customers/register/` | None | Register new customer |
| POST | `/api/customers/login/` | None | Login, get JWT tokens |
| GET | `/api/customers/profile/` | JWT | Get own profile |
| PUT | `/api/customers/profile/` | JWT | Update own profile |
| GET | `/api/customers/<id>/` | JWT | Get customer by ID |

### Product Service  `/api/products/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/products/` | None | List products (supports ?search=, ?category_id=, ?min_price=, ?max_price=, ?page=) |
| GET | `/api/products/<id>/` | None | Get product detail |
| POST | `/api/products/` | None | Create a product |
| PUT | `/api/products/<id>/` | None | Update product |
| DELETE | `/api/products/<id>/` | None | Soft-delete product |
| PATCH | `/api/products/<id>/inventory/` | None | Adjust stock (delta field) |

### Catalog Service  `/api/catalog/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/catalog/categories/` | None | List all categories (with children) |
| GET | `/api/catalog/categories/<id>/` | None | Category detail |
| POST | `/api/catalog/categories/` | None | Create category |
| PUT | `/api/catalog/categories/<id>/` | None | Update category |
| DELETE | `/api/catalog/categories/<id>/` | None | Delete category |

### Cart Service  `/api/cart/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/cart/<customer_id>/` | None | Get cart |
| POST | `/api/cart/<customer_id>/items/` | None | Add item to cart |
| PUT | `/api/cart/<customer_id>/items/<item_id>/` | None | Update item quantity |
| DELETE | `/api/cart/<customer_id>/items/<item_id>/` | None | Remove item from cart |
| DELETE | `/api/cart/<customer_id>/clear/` | None | Clear cart |

### Order Service  `/api/orders/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/orders/?customer_id=<id>` | None | List orders for customer |
| POST | `/api/orders/` | None | Create order from cart (triggers pay + ship) |
| GET | `/api/orders/<id>/` | None | Get order detail |

### Payment Service  `/api/payments/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/payments/<id>/` | None | Get payment by ID |
| GET | `/api/payments/order/<order_id>/` | None | Get payment by order |

### Shipment Service  `/api/shipments/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/shipments/<id>/` | None | Get shipment detail |
| GET | `/api/shipments/order/<order_id>/` | None | Get shipment by order |
| PATCH | `/api/shipments/<id>/status/` | None | Update shipment status |
| GET | `/api/shipments/track/<tracking_number>/` | None | Track by tracking number |

### Reviews Service  `/api/reviews/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/reviews/ratings/?product_id=<id>` | None | Get ratings for a product |
| POST | `/api/reviews/ratings/` | None | Submit/update a rating |
| GET | `/api/reviews/ratings/product/<id>/summary/` | None | Rating summary for a product |
| GET | `/api/reviews/comments/?product_id=<id>` | None | Comments for a product |
| POST | `/api/reviews/comments/` | None | Post a comment |
| DELETE | `/api/reviews/comments/<id>/` | None | Delete a comment |

### Recommendations Service  `/api/recommendations/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/recommendations/<customer_id>/` | None | Get personalized product recommendations |
| GET | `/api/recommendations/<customer_id>/?refresh=true` | None | Force-recompute recommendations |

### Staff Service  `/api/staff/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/staff/register/` | None | Register staff member |
| POST | `/api/staff/login/` | None | Login, get JWT |
| GET | `/api/staff/` | JWT | List all active staff |
| GET | `/api/staff/<id>/` | JWT | Get staff member |
| PUT | `/api/staff/<id>/` | JWT | Update staff member |
| DELETE | `/api/staff/<id>/` | JWT | Deactivate staff member |
| PATCH | `/api/staff/inventory/<product_id>/` | JWT | Adjust product stock |

### Manager Service  `/api/managers/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/managers/register/` | None | Register manager |
| POST | `/api/managers/login/` | None | Login, get JWT |
| GET | `/api/managers/reports/sales/` | JWT | Sales/revenue report |
| GET | `/api/managers/reports/staff/` | JWT | Staff roster report |
| GET | `/api/managers/reports/customers/?id=<id>` | JWT | Customer lookup |

### Gateway Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/` | Health check for all downstream services |

---

## Example Request/Response

### POST /api/customers/register/
```json
// Request
{
  "email": "alice@example.com",
  "password": "securePass123",
  "password_confirm": "securePass123",
  "first_name": "Alice",
  "last_name": "Smith",
  "phone": "+1-555-0100",
  "address": "123 Main St, Springfield"
}

// Response 201
{
  "customer": {
    "id": 1,
    "email": "alice@example.com",
    "first_name": "Alice",
    "last_name": "Smith",
    "phone": "+1-555-0100",
    "address": "123 Main St, Springfield",
    "created_at": "2026-03-12T10:00:00Z"
  },
  "tokens": {
    "refresh": "eyJ...",
    "access": "eyJ..."
  }
}
```

### POST /api/products/
```json
// Request
{
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "isbn": "9780134494166",
  "price": "35.99",
  "category_id": 2,
  "description": "A guide to software architecture.",
  "language": "English",
  "pages": 432,
  "stock_quantity": 50
}

// Response 201
{
  "id": 7,
  "title": "Clean Architecture",
  "author": "Robert C. Martin",
  "isbn": "9780134494166",
  "price": "35.99",
  "category_id": 2,
  "inventory": { "stock_quantity": 50, "warehouse_location": "" },
  "created_at": "2026-03-12T10:05:00Z"
}
```

### POST /api/cart/1/items/
```json
// Request
{ "product_id": 7, "quantity": 2, "unit_price": "35.99" }

// Response 201
{
  "id": 1,
  "customer_id": 1,
  "items": [
    { "id": 1, "product_id": 7, "quantity": 2, "unit_price": "35.99", "subtotal": "71.98" }
  ],
  "total_price": "71.98"
}
```

### POST /api/orders/
```json
// Request
{
  "customer_id": 1,
  "shipping_address": "123 Main St, Springfield",
  "payment_method": "CREDIT_CARD"
}

// Response 201
{
  "id": 42,
  "customer_id": 1,
  "status": "SHIPPED",
  "total_amount": "71.98",
  "shipping_address": "123 Main St, Springfield",
  "payment_method": "CREDIT_CARD",
  "items": [
    { "id": 1, "product_id": 7, "product_title": "Clean Architecture", "quantity": 2, "unit_price": "35.99", "subtotal": "71.98" }
  ],
  "created_at": "2026-03-12T10:10:00Z"
}
```

### POST /api/reviews/ratings/
```json
// Request
{ "product_id": 7, "customer_id": 1, "score": 5 }

// Response 201
{ "id": 1, "product_id": 7, "customer_id": 1, "score": 5, "created_at": "2026-03-12T10:15:00Z" }
```

### GET /api/recommendations/1/
```json
// Response 200
{
  "customer_id": 1,
  "strategy": "collaborative_filtering",
  "recommendations": [
    { "product_id": 3, "score": 0.9512, "title": "The Pragmatic Programmer", "brand": "Hunt & Thomas", "price": "42.00" },
    { "product_id": 11, "score": 0.8834, "title": "Design Patterns", "brand": "Gang of Four", "price": "49.99" }
  ]
}
```

---

## Quick Start

### Prerequisites
- Docker ≥ 24
- Docker Compose v2

### Launch the entire system

```bash
# Clone and enter the project
git clone <repo-url>
cd microservice-bookstore

# Build and start all 23 containers (11 services + 11 DBs + gateway)
docker compose up --build

# API is now available at http://localhost:8000
```

### Verify all services are running
```bash
curl http://localhost:8000/health/
```

### Stop everything
```bash
docker compose down -v   # -v also removes volumes (DBs)
```

---

## Project Structure

```
microservice-bookstore/
├── docker-compose.yml
├── README.md
├── api-gateway/                  # Reverse proxy — routes /api/<service>/...
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── entrypoint.sh
│   ├── manage.py
│   ├── config/
│   └── proxy/
├── customer-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── entrypoint.sh
│   ├── manage.py
│   ├── config/
│   └── customers/
│       ├── models.py             # Customer model (AbstractBaseUser)
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── internal_urls.py      # Called by peer services
│       ├── internal_views.py
│       └── services.py           # CartServiceClient
├── product-service/
│   └── books/                    # Book + BookInventory models
├── catalog-service/
│   └── catalog/                  # Category (hierarchical)
├── cart-service/
│   └── cart/                     # Cart + CartItem
├── order-service/
│   └── orders/                   # Order + OrderItem, orchestrates pay + ship
├── pay-service/
│   └── payments/                 # Payment with simulated gateway
├── ship-service/
│   └── shipments/                # Shipment + tracking
├── comment-rate-service/
│   └── reviews/                  # Rating + Comment
├── recommender-ai-service/
│   ├── recommender/
│   │   ├── engine.py             # Collaborative filtering + popularity fallback
│   │   └── views.py
│   └── requirements.txt          # Includes numpy + scikit-learn
├── staff-service/
│   └── staff/                    # StaffMember + inventory management
└── manager-service/
    └── management/               # Manager + aggregated reports
```

---

## AI Recommendation Engine

The `recommender-ai-service` implements a two-strategy recommendation pipeline:

**Strategy 1 — User-Based Collaborative Filtering:**
1. Fetch all orders from `order-service`
2. Build a customer × book binary purchase matrix
3. Compute cosine similarity between the target customer and all others
4. Recommend books purchased by similar customers but not yet by target

**Strategy 2 — Popularity Fallback:**
When the customer has no order history (cold start), returns books ranked by total purchase frequency across all customers.

Results are cached in PostgreSQL to avoid recomputing on every request. Pass `?refresh=true` to force a fresh computation.

---

## Environment Variables

Each service reads configuration from environment variables (set in `docker-compose.yml`):

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` / `False` |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | PostgreSQL host (Docker service name) |
| `DB_PORT` | PostgreSQL port (default `5432`) |
| `*_SERVICE_URL` | URL to peer services |

---

## Production Hardening Checklist

- [ ] Set `DEBUG=False` and use strong `SECRET_KEY` values
- [ ] Add service-to-service API key authentication (X-Internal-Token header)
- [ ] Replace `CORS_ALLOW_ALL_ORIGINS = True` with explicit allowed origins
- [ ] Add rate limiting (e.g., `djangorestframework-throttling`)
- [ ] Add centralized logging (ELK stack or CloudWatch)
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Add a message broker (Celery + Redis) for async inter-service events
- [ ] Configure PostgreSQL connection pooling (PgBouncer)
- [ ] Add TLS termination at the gateway
- [ ] Use Kubernetes for orchestration at scale
