# Contract API và SSE

## Địa chỉ và phiên bản

Client production gọi API cùng origin `https://hanoi-land-law.pages.dev`; Cloudflare Function chuyển tiếp tới backend. Các route giữ tiền tố `/api/v1/`. Trường `api_version: 2` trong status mô tả contract chat có client history và request ID, không phải tiền tố URL mới.

Trong development, Vite proxy tới FastAPI local và OpenAPI được bật tại `/docs`. Production không mở trang OpenAPI.

Mọi `/api/` request production cần chữ ký ingress. Client sử dụng bearer token cho các thao tác phiên và chat; không tự tạo chữ ký hoặc gọi vòng qua Render. Request body giới hạn 64 KiB.

## Endpoint

| Method và đường dẫn | Xác thực client | Kết quả |
|---|---|---|
| `GET /healthz` | Không | Liveness; không chứng minh provider hoạt động |
| `GET /readyz` | Không | Trạng thái DB, cấu hình model, corpus và publication metadata |
| `POST /api/v1/sessions` | Turnstile khi production | Tạo phiên và cấp bearer token |
| `GET /api/v1/sessions/{session_id}` | Bearer | Xác nhận quyền truy cập phiên, không trả nội dung |
| `POST /api/v1/chat` | Bearer | Luồng SSE cho một lượt hỏi |
| `GET /api/v1/sessions/{session_id}/messages` | Không cung cấp nội dung | `410 Gone` |
| `GET /api/v1/sessions/{session_id}/traces/{trace_id}` | Không cung cấp nội dung | `410 Gone` |
| `GET /api/v1/documents` | Không yêu cầu bearer | `documents` của active corpus và `references` chỉ để đọc bản gốc |
| `GET /api/v1/documents/{document_id}` | Không yêu cầu bearer | Văn bản, chunk và quan hệ; hỗ trợ query `locator` |
| `GET /api/v1/projects` | Không yêu cầu bearer | Danh mục chỉ chứa `ring4` |
| `GET /api/v1/status` | Không yêu cầu bearer | Khả năng generation, lý do hạn chế và thời gian chờ |
| `GET /api/v1/evaluations/latest` | Không yêu cầu bearer | Báo cáo và trạng thái khớp corpus/fingerprint |

Các endpoint không yêu cầu bearer vẫn chịu kiểm tra ingress production.

## Tạo phiên

```http
POST /api/v1/sessions
Content-Type: application/json

{"turnstile_token":"<token do widget cấp>"}
```

Production kiểm tra token với Turnstile, hostname được cấu hình và action `create_session`. Phản hồi `201` gồm `session_id`, `token` và `retention_days`. Bearer token được giữ trong `sessionStorage`, hoặc bộ nhớ tab khi storage bị chặn; không đưa token vào URL, log hoặc lịch sử hội thoại.

Tạo cuộc trò chuyện mới ở frontend không tạo lại phiên API và không đặt lại quota phiên. Token không hợp lệ hoặc không có quyền trên phiên trả `404`.

Khi phiên hết hạn, client bỏ token, giữ lại bản nháp và yêu cầu người dùng gửi lại sau xác minh; không tự phát lại POST chat. Widget lỗi có nút thử tải lại.

## Thư viện nguồn

`GET /api/v1/documents` trả `documents` đã lập chỉ mục và `references` từ danh mục nguồn chính thức trong phạm vi. Reference có `availability=reference_only`, `applicability_verified=false`, `attachment_urls` công khai và không có chunk chứng cứ. Endpoint chi tiết hỗ trợ cả hai loại; reference trả `chunks=[]`, `relations=[]`. Không đưa reference vào retrieval hoặc citation của AI trước khi ingest/rà soát. Đường dẫn raw nội bộ và ghi chú xử lý không được trả qua API.

## Gửi câu hỏi

```json
{
  "session_id": "<session_id được cấp>",
  "request_id": "37e7c591-849e-4b40-9359-0ba955e38c43",
  "message": "Chi phí di chuyển tài sản được quy định thế nào?",
  "project": "ring4",
  "as_of": null,
  "history": []
}
```

Gửi `Authorization: Bearer <token>` và `Content-Type: application/json`.

| Trường | Quy tắc |
|---|---|
| `session_id` | ID của phiên đã được cấp, dài 32–40 ký tự |
| `request_id` | UUID do client tạo; bắt buộc gửi rõ trong production |
| `message` | 1–4.000 ký tự |
| `project` | `ring4` hoặc `null`; giá trị khác bị từ chối |
| `as_of` | Ngày ISO `YYYY-MM-DD` hoặc `null` để dùng ngày hiện tại của hệ thống |
| `mode` | Nếu có, chỉ nhận `agentic` |
| `history` | Tối đa 8 message; tổng nội dung tối đa 12.000 ký tự |

History phải gồm các cặp `user` → `assistant` và kết thúc bằng `assistant`. Mỗi message có `content` dài 1–3.000 ký tự, `as_of` tùy chọn và tối đa 8 citation metadata gồm `document_id`, `document_number`, `locator`. Không gửi trace hoặc bearer token trong history.

Assistant message và citation từ client không phải chứng cứ. Chúng chỉ hỗ trợ ngữ cảnh; hệ thống phải truy xuất và verify lại kết luận mới.

## SSE

Khi request được chấp nhận, response có `Content-Type: text/event-stream`.

| Sự kiện | Payload | Cách xử lý |
|---|---|---|
| `progress` | `step`, `tool`, `summary`, `document_ids`, `elapsed_ms` | Hiển thị bước thực thi; không phải đáp án |
| `result` | Kết quả cuối, citation, trace và telemetry | Lưu tại client và hiển thị kết quả |
| `failure` | Mã lỗi và thông báo lượt không hoàn tất | Thông báo lỗi; không tự gửi lại |
| SSE comment | `: connected` hoặc `: heartbeat` | Giữ kết nối; không có nội dung trả lời |

`result.status` có thể là `answered`, `clarification_needed`, `insufficient_evidence`, `limited` hoặc `error`. HTTP `200` của stream không đồng nghĩa câu hỏi đã được trả lời thành công; client phải kiểm tra sự kiện cuối và status.

Kết quả gồm `content`, `citations`, `trace`, `trace_id`, corpus/model identity và các chỉ số `llm_calls`, `tool_calls`, `token_usage`, `elapsed_ms`. Citation chứa nguồn, locator, excerpt, ngày kiểm tra và trang/URL nguồn bổ sung khi có. Schema chi tiết nằm trong `backend/landlaw/models.py`.

`citation.source_url` trỏ tới đúng trang PDF gốc (`#page=...`) khi có attachment được kiểm tra, hoặc tới ảnh trang gốc nếu nguồn công bố bằng ảnh. Client hiển thị liên kết “Mở trang nguồn gốc”; không suy định mọi URL này đều là PDF ký số. Không có ánh xạ xuất xứ chính xác thì trường này để trống.

## Gửi trùng, hủy và mất kết nối

Một phiên chỉ có một lượt đang chạy. Lease tự hết hạn khi worker không hoàn tất. Trong thời gian metadata còn được lưu, cùng `request_id` không được gọi LLM lần nữa, kể cả lượt trước đã lỗi. Request trùng hoặc phiên bận trả `409` và không cung cấp replay. Đây không phải cam kết chống trùng vĩnh viễn sau khi metadata đã được cleanup; client phải tạo UUID mới cho mỗi lượt mới.

Khi hủy, client đóng stream. Khi mất kết nối trước kết quả cuối, client không thể lấy đáp án từ server. Chỉ gửi UUID mới khi người dùng chủ động tạo lượt mới; không tự retry POST chat sau lỗi mạng.

`X-Request-ID` của HTTP phục vụ đối chiếu log và khác UUID `request_id` trong body dùng cho idempotency.

## Lỗi trước khi mở stream

| HTTP | Trường hợp | Xử lý client |
|---|---|---|
| `400` | `challenge_required`, `challenge_failed` | Hoàn tất hoặc làm mới xác minh trình duyệt |
| `403` | `untrusted_ingress` | Kiểm tra đường proxy và cấu hình; không gọi trực tiếp Render |
| `404` | Phiên không hợp lệ hoặc tài liệu không có | Không suy ra quyền truy cập phiên khác |
| `408` | `body_timeout` | Request body chưa đọc xong trong giới hạn |
| `409` | Request đã dùng, đang chạy hoặc `session_busy` | Không tự phát lại lượt |
| `410` | `browser_history_only` | Đọc lịch sử/trace tại IndexedDB |
| `413` | `body_too_large` | Giảm payload |
| `422` | `invalid_request` | Sửa cấu trúc hoặc giới hạn trường |
| `426` | `client_upgrade_required` | Tải lại client có hỗ trợ request ID |
| `429` | Quota hoặc `system_busy` | Tôn trọng `Retry-After` |
| `503` | `generation_disabled`, `challenge_unavailable` hoặc lỗi dịch vụ | Hiển thị giới hạn; thư viện nguồn vẫn có thể truy cập |

Payload lỗi validation chỉ chứa vị trí và loại lỗi, không echo nội dung đầu vào. Giới hạn provider phát sinh sau khi mở stream được phản ánh trong kết quả hoặc lỗi SSE, không nhất thiết bằng HTTP `429`.
