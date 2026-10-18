# ADR 0003: Ingress có chữ ký và quota theo vai trò thực thi

**Trạng thái:** Chấp nhận

## Bối cảnh

API công khai không đăng nhập cần giới hạn lạm dụng và bảo vệ ngân sách provider. Công việc phát triển, kiểm thử và đánh giá cần usage riêng để không tiêu hoặc bị chặn bởi ngân sách dành cho người dùng trải nghiệm.

## Quyết định

Cloudflare Pages Function là ingress cho API production và ký HMAC tới Render. Backend chỉ tin IP được đưa vào chữ ký đã kiểm tra. Turnstile được xác minh server-side khi tạo phiên.

API cố định scope `public`; trusted CLI/dev entrypoint dùng `operator`. Scope không được chọn qua header hoặc body của client. Hai scope ghi usage riêng; quota ứng dụng public không áp dụng cho operator. Giới hạn thực tế của Groq và `Retry-After` áp dụng cho cả hai.

## Phương án không chọn

Không cho browser gọi trực tiếp Render, không dùng IP do client tự khai báo và không dùng cùng counters public cho các lượt đánh giá. Không xoay key hoặc retry liên tục để vượt giới hạn provider.

## Hệ quả

- Ingress secret phải được cấu hình đồng nhất và quản lý như backend credential; không được đưa vào frontend bundle.
- Cần kiểm tra cả ingress, session, body size, idempotency và concurrency; HMAC không thay thế các cơ chế này.
- Managed Turnstile có thể chặn kiểm tra tự động cho tới khi có tương tác. Không dùng test key để khiến production smoke đạt.
- Ngưỡng token dựa trên usage đã ghi nhận không phải trần chi phí tuyệt đối.
- Có thể tạm tắt public generation trong cửa sổ đánh giá để giảm cạnh tranh quota provider.

## Kiểm chứng

Kiểm tra direct Render, chữ ký/IP bị sửa, Turnstile không hợp lệ, client tự khai operator, public quota cạn và operator vẫn hoạt động. Các giá trị quota và cách xử lý sự cố nằm trong [runbook](../OPERATIONS.md).
