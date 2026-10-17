# API v2 và SSE

Production gọi cùng origin Cloudflare. Health/readiness phục vụ quan sát; mọi `/api/` cần chữ ký ingress hợp lệ. Body tối đa 64 KiB. Client không được chọn chế độ operator.

| Endpoint | Contract |
|---|---|
| `POST /api/v1/sessions` | JSON `turnstile_token`; kiểm tra hostname/action server-side; trả `session_id`, bearer `token` |
| `GET /api/v1/sessions/{id}` | Bearer; chỉ xác nhận phiên, không trả nội dung |
| `POST /api/v1/chat` | Bearer; JSON dưới đây; SSE |
| `GET /api/v1/sessions/{id}/messages` | `410 Gone`; history chỉ tại client |
| Endpoint trace cũ | `410 Gone`; trace xem trực tiếp trong IndexedDB |
| `GET /api/v1/documents` | Danh mục nguồn của active corpus |
| `GET /api/v1/documents/{id}` | Văn bản/đoạn nguồn |
| `GET /api/v1/status` | Trạng thái generation, freshness, provider cooldown |
| `GET /api/v1/evaluations/latest` | Báo cáo cùng cảnh báo corpus/configuration mismatch |

```json
{"session_id":"uuid","request_id":"uuid","message":"Chi phí di chuyển tài sản được quy định thế nào?","project":"ring4","as_of":null,"history":[]}
```

`history`: tối đa 8 message, bắt đầu user và xen kẽ assistant, kết thúc assistant, tổng 12.000 ký tự, mỗi message tối đa 3.000. Có thể gửi `as_of` và metadata citation; không gửi trace. Nội dung assistant/citation cũ không là bằng chứng cho lượt mới.

SSE có `progress` (sự kiện quan sát được), `result` (đáp án cuối + citations + trace + usage), `failure` (lỗi thực tế), heartbeat. Không phát answer draft. Chỉ một lượt chạy trong phiên; lease tự hết hạn nếu worker chết. UUID `request_id` đã dùng nhận `409`, kể cả lượt trước thất bại. Không lưu kết quả để replay. Sau mất kết nối chỉ gửi request mới khi người dùng chủ động.

Lỗi: `403 untrusted_ingress`, `400 challenge_*`, `413 body_too_large`, `408 body_timeout`, `422 invalid_request`, `426` client cần request_id, `409 request_* / session_busy`, `429` quota/provider cùng Retry-After, `503` dịch vụ chưa sẵn sàng. Không trả lại request body trong lỗi validation. Token sai không tiết lộ dữ liệu phiên khác.
