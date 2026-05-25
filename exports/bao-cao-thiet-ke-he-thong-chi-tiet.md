# 2. Phân tích và thiết kế hệ thống

## 2.1 Xác định yêu cầu

Phần này được tổng hợp từ mã nguồn hiện có của hệ thống `microservice-bookstore`, đặc biệt là các service `customer-service`, `catalog-service`, `product-service`, `cart-service`, `order-service`, `pay-service`, `ship-service`, `staff-service`, `manager-service`, `api-gateway` và frontend. Vì repository không chứa một tài liệu SRS riêng biệt, các yêu cầu dưới đây được suy ra trực tiếp từ hành vi hệ thống đang được cài đặt.

### 2.1.1 Functional Requirements

Hệ thống cần đáp ứng các yêu cầu chức năng chính sau:

1. Quản lý tài khoản khách hàng
  - Đăng ký tài khoản khách hàng.
  - Đăng nhập bằng email và mật khẩu.
  - Truy xuất và cập nhật hồ sơ cá nhân.
  - Tự động khởi tạo giỏ hàng cho khách hàng mới sau khi đăng ký.
2. Quản lý nhân sự nội bộ
  - Đăng ký và đăng nhập tài khoản nhân viên.
  - Phân vai trò nhân viên: `WAREHOUSE`, `SALES`, `SUPPORT`, `MANAGER`.
  - Cho phép nhân viên thực hiện nghiệp vụ cập nhật tồn kho thông qua `product-service`.
3. Quản lý tài khoản quản trị
  - Đăng ký và đăng nhập tài khoản manager.
  - Truy xuất báo cáo doanh thu, thông tin nhân sự và thông tin khách hàng.
4. Quản lý danh mục sản phẩm
  - Tạo, sửa, xóa danh mục.
  - Tổ chức danh mục theo cây phân cấp cha - con.
  - Cho phép truy xuất danh mục gốc kèm danh mục con.
5. Quản lý sản phẩm
  - Tạo mới sản phẩm.
  - Cập nhật thông tin sản phẩm.
  - Xóa mềm sản phẩm bằng cách chuyển `is_active=False`.
  - Liệt kê sản phẩm có hỗ trợ phân trang, lọc theo danh mục, loại sản phẩm, từ khóa, giá.
  - Tách phần tồn kho khỏi thông tin mô tả sản phẩm.
  - Cung cấp API nội bộ để các service khác lấy chi tiết một hoặc nhiều sản phẩm.
6. Quản lý giỏ hàng
  - Tạo giỏ hàng theo khách hàng.
  - Thêm sản phẩm vào giỏ.
  - Cập nhật số lượng từng item.
  - Xóa item khỏi giỏ.
  - Xóa toàn bộ giỏ sau khi checkout.
  - Tính tổng tiền của giỏ hàng.
7. Quản lý đơn hàng
  - Tạo đơn hàng từ dữ liệu giỏ hàng hoặc từ danh sách item truyền trực tiếp.
  - Lưu snapshot của sản phẩm trong thời điểm đặt hàng.
  - Theo dõi trạng thái đơn hàng.
  - Liệt kê đơn hàng theo khách hàng.
  - Cung cấp lịch sử đơn hàng nội bộ cho recommender.
8. Xử lý thanh toán
  - Tạo bản ghi thanh toán cho đơn hàng.
  - Hỗ trợ các phương thức: `CREDIT_CARD`, `DEBIT_CARD`, `PAYPAL`, `BANK_TRANSFER`, `COD`.
  - Truy vấn thanh toán theo `id` hoặc theo `order_id`.
  - Đảm bảo idempotency theo `order_id`.
9. Xử lý vận chuyển
  - Tạo shipment khi đơn hàng thanh toán thành công.
  - Sinh `tracking_number`.
  - Cập nhật trạng thái vận chuyển.
  - Theo dõi shipment theo `id`, `order_id` hoặc `tracking_number`.
10. Điều phối hệ thống qua API Gateway
  - Tất cả request public đi qua `api-gateway`.
  - Gateway định tuyến request đến đúng downstream service.
  - Gateway cung cấp endpoint kiểm tra health tổng thể.

### 2.1.2 Non-functional Requirements

Từ kiến trúc và cấu hình hiện tại, có thể xác định các yêu cầu phi chức năng sau:

1. Tính mô-đun cao
  - Hệ thống được tách thành nhiều microservice độc lập theo domain.
  - Mỗi service có DB riêng, hạn chế coupling ở tầng persistence.
2. Khả năng mở rộng
  - Có thể scale từng service độc lập như product, order, payment, shipping.
  - Gateway cho phép mở rộng thêm service mới bằng cách cập nhật service registry.
3. Tính sẵn sàng
  - Nếu một service downstream lỗi, gateway trả về `503` thay vì làm sập toàn hệ thống.
  - Order flow có cơ chế xử lý lỗi rõ ràng ở các bước payment, shipping, cart.
4. Tính nhất quán nghiệp vụ ở mức chấp nhận được cho microservice
  - Không dùng distributed transaction; thay vào đó dùng orchestration ở `order-service`.
  - Đổi lại hệ thống giữ được mức đơn giản khi triển khai.
5. Tính bảo trì
  - Các service đều dùng Django hoặc FastAPI với cấu trúc nhất quán.
  - Mỗi service có `models`, `serializers`, `views`, `urls` riêng.
6. Bảo mật cơ bản
  - Customer, staff và manager dùng JWT.
  - Product và catalog xác thực token do manager/staff phát hành cho thao tác ghi.
  - Tuy nhiên internal endpoints hiện để `AllowAny`, nên bảo mật đang dựa nhiều vào mạng nội bộ Docker hơn là zero-trust.
7. Hiệu năng ở mức ứng dụng nghiệp vụ vừa
  - Có phân trang danh sách sản phẩm.
  - Có internal bulk API ở product-service để giảm số lượng request liên service.
  - Chưa có cache phân tán hoặc message broker.
8. Triển khai thuận tiện
  - Toàn hệ thống được đóng gói bằng Docker Compose.
  - Mỗi service có container và Postgres riêng.

## 2.2 Phân rã hệ thống theo DDD

### 2.2.1 Bounded Context

Dựa trên mã nguồn hiện tại, hệ thống được phân rã theo các bounded context sau:

1. Customer Context
  - Quản lý tài khoản khách hàng, xác thực khách hàng, hồ sơ khách hàng.
  - Triển khai tại `customer-service`.
2. Staff Context
  - Quản lý tài khoản nhân viên và các vai trò nội bộ nghiệp vụ.
  - Triển khai tại `staff-service`.
3. Manager Context
  - Quản lý tài khoản quản trị và báo cáo tổng hợp.
  - Triển khai tại `manager-service`.
4. Catalog Context
  - Quản lý cây danh mục.
  - Triển khai tại `catalog-service`.
5. Product Context
  - Quản lý sản phẩm, thuộc tính sản phẩm, tồn kho.
  - Triển khai tại `product-service`.
6. Cart Context
  - Quản lý giỏ hàng tạm thời của khách hàng.
  - Triển khai tại `cart-service`.
7. Order Context
  - Quản lý vòng đời đơn hàng và điều phối checkout.
  - Triển khai tại `order-service`.
8. Payment Context
  - Quản lý thanh toán và transaction.
  - Triển khai tại `pay-service`.
9. Shipping Context
  - Quản lý giao vận và theo dõi shipment.
  - Triển khai tại `ship-service`.
10. Review Context
  - Quản lý đánh giá và nhận xét sản phẩm.
  - Triển khai tại `comment-rate-service`.
11. Recommendation Context
  - Quản lý recommendation và analytics recommendation.
  - Triển khai tại `recommender-ai-service`.
12. Conversational AI / RAG Context
  - Quản lý chatbot, retrieval và graph personalization.
  - Triển khai tại `rag-service` và `graph-rag-service`.

### 2.2.2 Nguyên tắc

Hệ thống đang tuân theo các nguyên tắc phân rã gần với DDD như sau:

1. Mỗi bounded context sở hữu database riêng
  - Không có bảng dùng chung giữa các service.
  - Tham chiếu liên service được lưu dưới dạng ID nguyên thủy, ví dụ `customer_id`, `product_id`, `order_id`.
2. Tách domain model theo nghiệp vụ, không theo UI
  - `Product`, `Category`, `Cart`, `Order`, `Payment`, `Shipment` là các aggregate tách biệt.
3. Giao tiếp liên context qua HTTP API
  - `order-service` gọi `cart-service`, `pay-service`, `ship-service`.
  - `customer-service` gọi `cart-service` để tạo giỏ.
  - `manager-service` gọi `order-service`, `staff-service`, `customer-service`.
4. Dùng orchestration thay cho distributed transaction
  - `order-service` là coordinator của checkout workflow.
  - Đây là quyết định thực dụng, giảm độ phức tạp triển khai.
5. Dùng soft delete khi phù hợp
  - `product-service` và `customer-service` không xóa cứng một số thực thể public, mà chuyển `is_active=False`.
6. Phân quyền theo context phát hành token
  - Customer, staff và manager phát hành JWT riêng ở service của mình.
  - Product và catalog chỉ xác thực token ở mức hợp lệ, không áp chi tiết role claim trong mã hiện tại.

## 2.3 Thiết kế Product Service (Django)

`product-service` chịu trách nhiệm quản lý thông tin sản phẩm và tồn kho. Service được triển khai bằng Django REST Framework, lưu dữ liệu vào PostgreSQL riêng.

### 2.3.1 Phân loại sản phẩm

Hệ thống hiện hỗ trợ 6 loại sản phẩm thông qua `ProductType`:

- `BOOK`
- `ELECTRONICS`
- `CLOTHING`
- `FOOD`
- `HOME`
- `SPORTS`

Thiết kế này cho phép một service duy nhất phục vụ nhiều domain hàng hóa khác nhau, thay vì chỉ giới hạn trong sách. Tuy nhiên repo hiện tại vẫn mang ngữ cảnh bookstore, nên loại `BOOK` đang là loại sản phẩm trung tâm.

### 2.3.2 Model tổng quát

Product Service có 2 model chính:

1. `Product`
  - Thông tin mô tả và kinh doanh của sản phẩm.
2. `ProductInventory`
  - Thông tin tồn kho, tách riêng theo quan hệ `OneToOne`.

Thiết kế này tách read model nghiệp vụ bán hàng khỏi nghiệp vụ kho, giúp giảm xung đột cập nhật.

### 2.3.3 Chi tiết theo domain

#### a. Product

Các thuộc tính chính:

- `title`: tên sản phẩm.
- `product_type`: loại sản phẩm.
- `sku`: mã hàng duy nhất.
- `description`: mô tả.
- `price`: giá bán.
- `cover_image`: URL ảnh đại diện.
- `category_id`: khóa ngoại logic sang `catalog-service`.
- `brand`: thương hiệu hoặc tác giả.
- `attributes`: JSON linh hoạt theo từng loại hàng.
- `is_active`: trạng thái hoạt động.
- `created_at`, `updated_at`.

Điểm đáng chú ý là `attributes` được dùng như extension point:

- sách có thể chứa `author`, `isbn`, `pages`, `language`;
- electronics có thể chứa `specs`, `warranty`;
- clothing có thể chứa `sizes`, `material`.

Đây là cách thiết kế phù hợp khi muốn giữ một aggregate chung nhưng vẫn hỗ trợ đa hình dữ liệu.

#### b. ProductInventory

Các thuộc tính chính:

- `product`
- `stock_quantity`
- `warehouse_location`
- `updated_at`

Tồn kho không nằm trực tiếp trong `Product`, nhờ đó các cập nhật kho có thể được tách biệt về trách nhiệm.

### 2.3.4 API

Public / gateway API:

1. `GET /api/products/`
  - Liệt kê sản phẩm.
  - Hỗ trợ filter:
    - `category_id`
    - `product_type`
    - `search`
    - `min_price`
    - `max_price`
    - `page`
    - `page_size`
  - Nếu request không authenticated, chỉ trả sản phẩm `is_active=True`.
2. `POST /api/products/`
  - Tạo sản phẩm mới.
  - Có thể đồng thời truyền `stock_quantity` và `warehouse_location`.
3. `GET /api/products/{id}/`
  - Lấy chi tiết sản phẩm.
4. `PUT /api/products/{id}/`
  - Cập nhật sản phẩm.
5. `DELETE /api/products/{id}/`
  - Xóa mềm sản phẩm bằng cách set `is_active=False`.
6. `PATCH /api/products/{id}/inventory/`
  - Điều chỉnh tồn kho bằng `delta`.
  - Từ chối nếu tồn kho sau cập nhật nhỏ hơn 0.

Internal API:

1. `GET /internal/products/{id}/`
  - Lấy chi tiết một sản phẩm.
2. `POST /internal/products/bulk/`
  - Lấy thông tin nhiều sản phẩm theo danh sách `ids`.

Về phân quyền:

- Read mở cho mọi người.
- Write yêu cầu Bearer token hợp lệ được ký bởi `manager-service` hoặc `staff-service`.
- Mã hiện tại chỉ kiểm tra token hợp lệ và `is_authenticated`, chưa kiểm tra role chi tiết.

## 2.4 Thiết kế User Service (Django)

Lưu ý kiến trúc: hệ thống thực tế không có một `user-service` duy nhất. User domain được tách làm 3 service:

- `customer-service`
- `staff-service`
- `manager-service`

Trong báo cáo này, mục “User Service” sẽ được mô tả như một user domain phân rã theo DDD, thay vì một monolith auth service.

### 2.4.1 Phân loại người dùng

Hệ thống có 3 nhóm người dùng chính:

1. Customer
  - Người mua hàng cuối.
  - Có hồ sơ cá nhân, địa chỉ, số điện thoại.
  - Có giỏ hàng và đơn hàng.
2. Staff
  - Nhân sự vận hành.
  - Có các role:
    - `WAREHOUSE`
    - `SALES`
    - `SUPPORT`
    - `MANAGER`
3. Manager
  - Người quản trị cấp cao.
  - Có quyền xem báo cáo doanh thu, nhân sự và khách hàng.

Phân loại này phản ánh rõ nhu cầu tách actor theo nghiệp vụ, thay vì nhồi tất cả vào một bảng user với quá nhiều cột và cờ quyền.

### 2.4.2 Model

#### a. Customer model

`customer-service` sử dụng custom user `Customer`, kế thừa `AbstractBaseUser`.

Các thuộc tính chính:

- `email`
- `first_name`
- `last_name`
- `phone`
- `address`
- `is_active`
- `created_at`
- `updated_at`

Đặc điểm:

- `USERNAME_FIELD = email`
- không có quyền staff/admin trong nội bộ Django
- khi đăng ký sẽ tự tạo cart ở `cart-service`

#### b. Staff model

`staff-service` sử dụng custom user `StaffMember`.

Các thuộc tính chính:

- `email`
- `first_name`
- `last_name`
- `role`
- `is_active`
- `is_admin`
- `created_at`
- `updated_at`

Đặc điểm:

- `role` là trung tâm cho phân quyền nội bộ nghiệp vụ.
- `is_admin` được dùng cho permission Django backend.

#### c. Manager model

`manager-service` sử dụng custom user `ManagerUser`.

Các thuộc tính chính:

- `email`
- `first_name`
- `last_name`
- `is_active`
- `created_at`

Đặc điểm:

- toàn bộ manager được xem như superuser trong context của chính service này.
- manager chủ yếu làm việc với báo cáo và orchestration ở tầng quản trị.

### 2.4.3 Phân quyền (RBAC)

Hệ thống dùng RBAC theo hướng tách theo service:

1. Customer RBAC
  - Khách hàng chỉ truy cập profile của chính mình qua JWT.
  - Các endpoint list/detail customer hiện để `AllowAny` trong mã nguồn, nên nếu đánh giá nghiêm ngặt thì đây là điểm cần siết lại.
2. Staff RBAC
  - Staff đăng nhập bằng JWT do `staff-service` phát hành.
  - `InventoryManagementView` yêu cầu `IsAuthenticated`.
  - Tuy nhiên chưa có kiểm tra chặt role `WAREHOUSE` hay `MANAGER` trong code.
3. Manager RBAC
  - Các endpoint báo cáo yêu cầu `IsAuthenticated`.
  - JWT do `manager-service` phát hành.
4. Cross-service write RBAC
  - `product-service` và `catalog-service` chấp nhận token do manager hoặc staff ký.
  - Việc xác thực được thực hiện bằng cách thử decode JWT bằng `MANAGER_JWT_SECRET` hoặc `STAFF_JWT_SECRET`.
  - Mức phân quyền hiện tại là coarse-grained: token hợp lệ thì cho phép ghi.

Kết luận RBAC:

- Hệ thống đã có nền JWT và phân tách actor rõ ràng.
- Nhưng enforcement theo role còn chưa chi tiết; đó là giới hạn hiện tại của implementation.

### 2.4.4 API

#### Customer API

- `POST /api/customers/register/`
- `POST /api/customers/login/`
- `GET /api/customers/profile/`
- `PUT /api/customers/profile/`
- `GET /api/customers/`
- `GET /api/customers/{id}/`
- `PUT /api/customers/{id}/`
- `DELETE /api/customers/{id}/`
- `GET /internal/customers/{id}/`

#### Staff API

- `POST /api/staff/register/`
- `POST /api/staff/login/`
- `GET /api/staff/`
- `GET /api/staff/{id}/`
- `PUT /api/staff/{id}/`
- `DELETE /api/staff/{id}/`
- `PATCH /api/staff/inventory/{product_id}/`
- `GET /internal/staff/`

#### Manager API

- `POST /api/managers/register/`
- `POST /api/managers/login/`
- `GET /api/managers/reports/sales/`
- `GET /api/managers/reports/staff/`
- `GET /api/managers/reports/customers/?id={customer_id}`

## 2.5 Thiết kế Cart Service

`cart-service` quản lý trạng thái giỏ hàng tạm thời của khách hàng trước khi chuyển sang order.

### 2.5.1 Model

Cart Service có 2 model:

1. `Cart`
  - `customer_id`
  - `created_at`
  - `updated_at`
  - mỗi khách hàng chỉ có một cart duy nhất
2. `CartItem`
  - `cart`
  - `product_id`
  - `quantity`
  - `unit_price`
  - `added_at`

Ràng buộc:

- `unique_together = (cart, product_id)`

Điều này đảm bảo trong một cart không có 2 dòng item cho cùng một sản phẩm; thay vào đó quantity sẽ được cộng dồn.

### 2.5.2 Logic

Nghiệp vụ cart hiện khá gọn:

1. Khi customer đăng ký, `customer-service` gọi internal API để tạo cart trống.
2. Khi thêm sản phẩm:
  - nếu cart chưa tồn tại thì tạo mới;
  - nếu item chưa tồn tại thì thêm mới;
  - nếu item đã tồn tại thì cộng thêm quantity.
3. Khi cập nhật item:
  - chỉ cho phép set `quantity >= 1`.
4. Khi checkout xong:
  - `order-service` gọi `DELETE /api/cart/{customer_id}/clear/` để xóa toàn bộ item.

Thiết kế hiện tại lưu `unit_price` ngay tại cart item. Đây là quyết định hợp lý để giữ snapshot giá tại thời điểm người dùng thêm vào giỏ, dù giá sản phẩm sau đó có thể thay đổi.

### 2.5.3 API

Public / gateway API:

- `GET /api/cart/{customer_id}/`
- `POST /api/cart/{customer_id}/items/`
- `PUT /api/cart/{customer_id}/items/{item_id}/`
- `DELETE /api/cart/{customer_id}/items/{item_id}/`
- `DELETE /api/cart/{customer_id}/clear/`

Internal API:

- `POST /internal/carts/create/`
- `GET /internal/carts/{customer_id}/`

## 2.6 Thiết kế Order Service

`order-service` là service trung tâm của quy trình mua hàng. Nó đóng vai trò orchestration layer giữa cart, payment và shipping.

### 2.6.1 Model

Order Service có 2 model chính:

1. `Order`
  - `customer_id`
  - `status`
  - `total_amount`
  - `shipping_address`
  - `payment_method`
  - `created_at`
  - `updated_at`
2. `OrderItem`
  - `order`
  - `product_id`
  - `product_title`
  - `quantity`
  - `unit_price`

`OrderItem` lưu snapshot của title và price tại thời điểm đặt hàng, tránh phụ thuộc vào việc product thay đổi về sau.

Trạng thái đơn hàng:

- `PENDING`
- `CONFIRMED`
- `PAID`
- `SHIPPED`
- `DELIVERED`
- `CANCELLED`
- `REFUNDED`

### 2.6.2 Workflow

Workflow tạo đơn hàng đang được triển khai theo các bước sau:

1. Nhận request tạo order với:
  - `customer_id`
  - `shipping_address`
  - `payment_method`
  - tùy chọn `items`
2. Xác định nguồn item:
  - nếu request truyền `items`, dùng trực tiếp;
  - nếu không, gọi `cart-service` để lấy cart hiện tại.
3. Kiểm tra cart/item rỗng
  - nếu không có item thì trả lỗi `Cart is empty`.
4. Tính `total_amount`
  - cộng `unit_price * quantity` cho tất cả item.
5. Tạo `Order` và `OrderItem` trong transaction cục bộ.
6. Gọi `pay-service` để xử lý thanh toán
  - nếu payment fail, cập nhật order thành `CANCELLED`.
  - nếu payment service unavailable, cập nhật order thành `CANCELLED` và trả `503`.
7. Nếu thanh toán thành công:
  - cập nhật order thành `PAID`.
8. Gọi `ship-service` để tạo shipment
  - nếu thành công, cập nhật order thành `SHIPPED`.
  - nếu lỗi shipping, log warning nhưng không rollback payment.
9. Xóa giỏ hàng ở `cart-service`.

Nhận xét kiến trúc:

- Đây là orchestration đồng bộ, đơn giản và dễ hiểu.
- Đổi lại chưa có saga thực thụ hay compensation flow ngoài việc mark `CANCELLED`.

API:

- `GET /api/orders/?customer_id={id}`
- `POST /api/orders/`
- `GET /api/orders/{id}/`
- `PUT /api/orders/{id}/`
- `GET /internal/orders/customer/{customer_id}/history/`

## 2.7 Thiết kế Payment Service

`pay-service` lưu và xử lý thanh toán theo kiểu mock gateway.

### 2.7.1 Model

Model `Payment` gồm:

- `order_id`
- `customer_id`
- `amount`
- `status`
- `method`
- `transaction_id`
- `created_at`
- `updated_at`

Ràng buộc:

- `order_id` là `unique`, tức một order chỉ có một payment record chính.
- `transaction_id` là UUID duy nhất.

### 2.7.2 Trạng thái

Payment hỗ trợ các trạng thái:

- `PENDING`
- `COMPLETED`
- `FAILED`
- `REFUNDED`

Logic xử lý hiện tại:

- Nếu phương thức là `COD`, thanh toán được coi là thành công ngay.
- Nếu là phương thức online khác, hệ thống mô phỏng gateway với xác suất thành công 90%.
- Nếu cùng `order_id` được gọi lại, service trả về bản ghi thanh toán đã có, tức có tính idempotency mức cơ bản.

### 2.7.3 API

Public / gateway API:

- `GET /api/payments/{id}/`
- `GET /api/payments/order/{order_id}/`

Internal API:

- `POST /internal/payments/process/`

Input internal process:

- `order_id`
- `customer_id`
- `amount`
- `method`

## 2.8 Thiết kế Shipping Service

`ship-service` quản lý lô vận chuyển phát sinh sau khi thanh toán.

### 2.8.1 Model

Model `Shipment` gồm:

- `order_id`
- `customer_id`
- `shipping_address`
- `status`
- `tracking_number`
- `carrier`
- `estimated_delivery`
- `created_at`
- `updated_at`

Ràng buộc:

- `order_id` là duy nhất, tương ứng một order một shipment.
- `tracking_number` là UUID duy nhất.

### 2.8.2 Trạng thái

Shipment hỗ trợ các trạng thái:

- `PENDING`
- `PROCESSING`
- `SHIPPED`
- `IN_TRANSIT`
- `DELIVERED`
- `RETURNED`

Khi `order-service` gọi tạo shipment:

- service tạo shipment mới với carrier mặc định `BookStore Logistics`
- `estimated_delivery = current_date + 5 ngày`
- nếu shipment của order đã tồn tại thì trả về shipment cũ

Điều này đảm bảo create shipment cũng có tính idempotency cơ bản.

### 2.8.3 API

Public / gateway API:

- `GET /api/shipments/{id}/`
- `PATCH /api/shipments/{id}/status/`
- `GET /api/shipments/order/{order_id}/`
- `GET /api/shipments/track/{tracking_number}/`

Internal API:

- `POST /internal/shipments/create/`

Input internal create:

- `order_id`
- `customer_id`
- `shipping_address`
- `carrier` tùy chọn

## 2.9 Luồng hệ thống tổng thể

Luồng hệ thống tổng thể có thể mô tả theo các trục chính sau:

### 1. Trục truy cập client

1. Người dùng truy cập frontend React.
2. Frontend gửi request đến `api-gateway`.
3. `api-gateway` tra `SERVICE_REGISTRY` để forward request đến đúng service.
4. Kết quả từ service downstream được trả ngược về frontend.

Ưu điểm:

- client chỉ cần biết một entrypoint.
- thay đổi vị trí nội bộ của service không ảnh hưởng frontend nếu registry vẫn đúng.

### 2. Trục quản lý danh mục và sản phẩm

1. Manager hoặc staff đăng nhập và lấy JWT.
2. Với token hợp lệ, họ gọi:
  - `catalog-service` để tạo/cập nhật category,
  - `product-service` để tạo/cập nhật product.
3. Product liên kết với category qua `category_id`.
4. Inventory được cập nhật riêng qua API tồn kho.

### 3. Trục khách hàng và giỏ hàng

1. Khách hàng đăng ký qua `customer-service`.
2. `customer-service` gọi `cart-service` tạo cart trống.
3. Khách hàng thêm item vào giỏ hàng qua `cart-service`.
4. Giỏ hàng lưu snapshot `unit_price`, `quantity` và `product_id`.

### 4. Trục checkout

1. Khách hàng gửi yêu cầu tạo order.
2. `order-service` lấy item từ request hoặc từ `cart-service`.
3. `order-service` tạo order nội bộ.
4. `order-service` gọi `pay-service`.
5. Nếu payment thành công:
  - order chuyển `PAID`,
  - gọi `ship-service` tạo shipment,
  - order có thể chuyển `SHIPPED`.
6. Sau cùng `order-service` gọi `cart-service` để clear cart.

Đây là luồng nghiệp vụ trung tâm của toàn hệ thống.

### 5. Trục quản trị

1. Manager đăng nhập ở `manager-service`.
2. Manager gọi các API báo cáo:
  - sales report từ `order-service`,
  - staff report từ `staff-service`,
  - customer report từ `customer-service`.
3. Nhờ đó manager-service đóng vai trò read-model / aggregation service cho tầng quản trị.

### 6. Trục AI mở rộng

Mặc dù không nằm trong form trọng tâm của mục 2.3 đến 2.8, hệ thống còn mở rộng thêm các service AI:

- `recommender-ai-service`
- `rag-service`
- `graph-rag-service`

Các service này sử dụng dữ liệu từ order, product, customer và catalog để cung cấp recommendation và chatbot. Điều này cho thấy kiến trúc đã sẵn sàng để mở rộng từ core commerce sang intelligent commerce.

### 7. Đánh giá tổng thể thiết kế

Từ mã nguồn hiện tại có thể kết luận:

1. Hệ thống được phân rã hợp lý theo domain nghiệp vụ.
2. `order-service` được đặt đúng vai trò orchestration trung tâm.
3. Tách DB theo service là quyết định phù hợp với DDD và microservice.
4. Các aggregate chính được mô hình hóa rõ ràng, không bị nhập nhằng trách nhiệm.
5. Phần RBAC và internal security đã có nền nhưng chưa hoàn thiện đến mức production-grade.
6. Hệ thống phù hợp cho đồ án, demo kiến trúc microservice, và có nền để tiếp tục nâng cấp theo hướng production.

