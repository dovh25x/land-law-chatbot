# Contract API và SSE

## Địa chỉ và phiên bản

Client production gọi API cùng origin `https://hanoi-land-law.pages.dev`; Cloudflare Function chuyển tiếp tới backend. Các route giữ tiền tố `/api/v1/`. Trường `api_version: 3` trong status mô tả contract chat có client history, request ID và projection đáp án cho người dân, không phải tiền tố URL mới.

Trong development, Vite proxy tới FastAPI local và OpenAPI được bật tại `/docs`. Production không mở trang OpenAPI.

Mọi `/api/` request production cần chữ ký ingress. Client sử dụng bearer token cho các thao tác phiên và chat; không tự tạo chữ ký hoặc gọi vòng qua Render. Request body giới hạn 64 KiB.

> **Đã phát hành PR #13:** contract claim-aware, marker nhóm và fallback ngắn đã deploy tại SHA `1a9718f03ed261f3511598488ab273b6bf5e0b92`; response `agentic_rag` vẫn dùng `answer_schema_version=1`. `/api/v1/evaluations/latest` có thể trả mode/fingerprint của báo cáo lịch sử: không dùng chúng thay cho runtime cấu hình và `active_configuration_sha256`. Xem [receipt public](../reports/releases/academic-mvp-1a9718f/README.md).

## Endpoint

| Method và đường dẫn | Xác thực client | Kết quả |
|---|---|---|
| `GET /healthz` | Không | Liveness; không chứng minh provider hoạt động |
| `GET /readyz` | Không | Trạng thái DB, cấu hình model, corpus và publication metadata |
| `POST /api/v1/sessions` | Turnstile khi production và `SESSION_CHALLENGE_MODE=turnstile`; bearer không bắt buộc | Tạo phiên và cấp bearer token |
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

`/readyz` bổ sung `configuration_sha256` và `source_gate`. Khi có policy nguồn giới hạn, `source_gate` gồm `mode`, `review_mode`, `policy_sha256`, `eligible_passages`, `usable`, `reviewed_at`, `reviewed_as_of`, `operational_expiry` và `whole_corpus_verified`; khi không cấu hình policy, giá trị là `null`. Với policy v2 `standing_verified_snapshot`, `operational_expiry` là `null` vì tuổi receipt không còn làm hết hiệu lực; `eligible_passages` chỉ đếm đoạn khớp checksum, receipt mới nhất và hiệu lực pháp lý tại ngày xem xét. `/api/v1/status` trả cùng summary policy, `source_review` và `session_challenge_mode`. Generation có thể khả dụng cho phạm vi đã duyệt trong khi `source_fresh=false` vẫn phản ánh toàn corpus chưa fresh. Mỗi claim còn phải qua kiểm tra đoạn và ngày hỏi; `usable=true` hoặc HTTP200 không chứng nhận độ đúng pháp luật hay toàn bộ coverage.

## Tạo phiên

```http
POST /api/v1/sessions
Content-Type: application/json

{"turnstile_token":"<token do widget cấp>"}
```

Khi `SESSION_CHALLENGE_MODE=turnstile`, production kiểm tra token với Turnstile, hostname được cấu hình và action `create_session`. Khi mode `disabled` (demo đã được duyệt), client gửi POST không body và backend không đọc token; session, token, expiry và mọi quota vẫn được cấp. Phản hồi `201` gồm `session_id`, `token` và `retention_days`. Bearer token được giữ trong `sessionStorage`, hoặc bộ nhớ tab khi storage bị chặn; không đưa token vào URL, log hoặc lịch sử hội thoại.

Tạo cuộc trò chuyện mới ở frontend không tạo lại phiên API và không đặt lại quota phiên hoặc quota IP. Token không hợp lệ hoặc không có quyền trên phiên trả `404`.

Khi phiên hết hạn, client bỏ token, giữ lại bản nháp và yêu cầu người dùng gửi lại; không tự phát lại POST chat. Nếu challenge đang bật, lần gửi lại có thể cần xác minh lại; nếu tắt, không hiển thị bước xác minh.

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
| `mode` | `agentic_rag` là đường chạy production khi `EXECUTION_MODE=agentic_rag`: model chọn trả lời trực tiếp hoặc gọi tối đa hai tool đọc-only; bình thường 1 request xã giao hoặc 2 request pháp luật, hard ceiling 3. `simple_rag` là rollback mode: một lượt generation, tối đa 5 passage đã lọc, citation marker `[S1]`...`[S5]` chỉ trỏ vào context thực gửi. `agentic` là legacy. Cả hai mode hiện hành đều suy citation từ marker inline, không nhận danh sách citation thứ hai từ model. Ở `agentic_rag`, câu khẳng định pháp lý cần marker trong câu; câu hỏi làm rõ có thể không có marker. Marker nhóm `[S1, S2]` được chấp nhận; ID ngoài context bị từ chối |
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

`result.status` có thể là `answered`, `clarification_needed`, `insufficient_evidence`, `limited` hoặc `error`. HTTP `200` của stream không đồng nghĩa câu hỏi đã được trả lời thành công; client phải kiểm tra sự kiện cuối và status. `clarification_needed` có hai dạng: câu hỏi làm rõ không marker (citations có thể rỗng) hoặc fallback an toàn sau validation thất bại (citations chỉ là danh tính nguồn đã đối chiếu, không phải kết luận).

Kết quả gồm `content`, `citations`, `trace`, `trace_id`, corpus/model identity và các chỉ số `llm_calls`, `tool_calls`, `token_usage`, `elapsed_ms`. Citation chứa nguồn, locator, excerpt, ngày kiểm tra và trang/URL nguồn bổ sung khi có. Schema chi tiết nằm trong `backend/landlaw/models.py`.

`trace` là chẩn đoán vận hành đã redact: reason code validation, số marker/claim và document ID; không chứa draft, excerpt hay nội dung hội thoại. Client không hiển thị các reason code này như lời giải thích pháp lý hoặc lỗi cho người dân.

`agentic_rag` là execution mode đích: model chọn tool nhưng ứng dụng thực thi, giới hạn request/tool và vẫn kiểm tra source review, applicability, citation/reference guard trước khi phát hành. `simple_rag` là rollback mode ít request hơn nhưng không có tool calling; cả hai giữ retrieval theo release, loại văn bản đã biết hết hiệu lực, không cho citation ngoài context và không kết luận quyền lợi cá nhân khi thiếu dữ kiện. Với snapshot v2, câu trả lời pháp luật có thể kèm một câu ghi mốc `reviewed_at` và khuyến nghị kiểm tra văn bản gốc; đây không phải tuyên bố snapshot là pháp luật hiện hành. Pilot model đã chạy và mode này đang phục vụ production; xem `reports/evaluation/agentic-rag-final/`. Đổi mode không biến retrieval accuracy thành answer accuracy.

`citation.source_url` trỏ tới đúng trang PDF gốc (`#page=...`) khi có attachment được kiểm tra, hoặc tới ảnh trang gốc nếu nguồn công bố bằng ảnh. Client hiển thị liên kết “Mở trang nguồn gốc”; không suy định mọi URL này đều là PDF ký số. Không có ánh xạ xuất xứ chính xác thì trường này để trống.

## Đáp án cấu trúc cho người dân

Status cung cấp `capabilities.citizen_answers=true`, `answer_schema_version=2`. Tuy nhiên `agentic_rag` hiện trả `answer_schema_version=1`, nên client dùng prose renderer; structured claim renderer version 2 chưa hoạt động trong production. Những lượt lỗi hoặc nhánh compatibility có thể vẫn dùng schema 1. Client chọn renderer theo version của từng result; dữ liệu v2 lỗi không fallback sang prose tự do.

`answer_sections` gồm tối đa ba nhóm `direct`, `explanation`, `actions`, chỉ tham chiếu index của `verified_claims`. Mỗi claim xuất hiện đúng một lần, section khớp claim và citation phải tồn tại trong cùng response. `answer_notices` chỉ chứa giới hạn cố định do runtime dựng, không phải summary/next_steps của model. `content` vẫn có để client cũ đọc cùng claim và giới hạn.

`clarification` là một câu hỏi làm rõ, tối đa ba lựa chọn cùng `allow_unknown`; client điền câu trả lời để người dùng sửa và gửi. `need_more_context` chỉ rõ fact còn thiếu hoặc `source`. `source_context` ghi ngày xem xét/kiểm tra thật, freshness, `source_review_mode` và `source_reviewed_at`; không chứng nhận quyền lợi. Citation có thêm `source_kind`; directory không chứng minh thẩm quyền.

Request nhận optional `interaction` với intent/stage có enum và độ dài giới hạn. Runtime hiện suy nhu cầu từ message/history user, không lấy interaction làm chứng cứ hoặc tự xác nhận hồ sơ.

## Gửi trùng, hủy và mất kết nối

Một phiên chỉ có một lượt đang chạy. Lease tự hết hạn khi worker không hoàn tất. Trong thời gian metadata còn được lưu, cùng `request_id` không được gọi LLM lần nữa, kể cả lượt trước đã lỗi. Request trùng hoặc phiên bận trả `409` và không cung cấp replay. Đây không phải cam kết chống trùng vĩnh viễn sau khi metadata đã được cleanup; client phải tạo UUID mới cho mỗi lượt mới.

Khi hủy, client đóng stream. Khi mất kết nối trước kết quả cuối, client không thể lấy đáp án từ server. Chỉ gửi UUID mới khi người dùng chủ động tạo lượt mới; không tự retry POST chat sau lỗi mạng.

`X-Request-ID` của HTTP phục vụ đối chiếu log và khác UUID `request_id` trong body dùng cho idempotency.

## Lỗi trước khi mở stream

| HTTP | Trường hợp | Xử lý client |
|---|---|---|
| `400` | `challenge_required`, `challenge_failed` khi challenge đang bật | Hoàn tất hoặc làm mới xác minh trình duyệt; mode `disabled` không trả các mã này |
| `403` | `untrusted_ingress` | Kiểm tra đường proxy và cấu hình; không gọi trực tiếp Render |
| `404` | Phiên không hợp lệ hoặc tài liệu không có | Không suy ra quyền truy cập phiên khác |
| `408` | `body_timeout` | Request body chưa đọc xong trong giới hạn |
| `409` | Request đã dùng, đang chạy hoặc `session_busy` | Không tự phát lại lượt |
| `410` | `browser_history_only` | Đọc lịch sử/trace tại IndexedDB |
| `413` | `body_too_large` | Giảm payload |
| `422` | `invalid_request` | Sửa cấu trúc hoặc giới hạn trường |
| `426` | `client_upgrade_required` | Tải lại client có hỗ trợ request ID |
| `429` | Quota hoặc `system_busy` | Tôn trọng `Retry-After` |
| `503` | `generation_disabled`, `challenge_unavailable` (chỉ khi challenge bật) hoặc lỗi dịch vụ | Hiển thị giới hạn; thư viện nguồn vẫn có thể truy cập |

Payload lỗi validation chỉ chứa vị trí và loại lỗi, không echo nội dung đầu vào. Giới hạn provider phát sinh sau khi mở stream được phản ánh trong kết quả hoặc lỗi SSE, không nhất thiết bằng HTTP `429`.

## Công bố số liệu đánh giá

`GET /api/v1/evaluations/latest` giữ các field summary cũ và bổ sung `runs`, `retrieval_runs`, `faithfulness_runs`, `sources`, `errata`, `default_run_id`. Mỗi run giữ corpus, model, backend, fingerprint, các suite và ca đã/chưa thực hiện; API gắn `matches_active_release`/`matches_active_configuration` theo deployment, không sửa identity artifact. Mặc định ưu tiên bộ đầy đủ khớp cả corpus và configuration, rồi mới cohort cùng corpus hoặc lần chạy còn dở.

`reports/public-evaluations.json` là bản chiếu public được tạo ngoại tuyến từ artifact đã commit; `sources` giữ đường dẫn GitHub ghim revision và SHA-256. Chỉ chứa câu hỏi benchmark khóa, nhận xét và chỉ số; không trả payload đáp án, hội thoại, token phiên hoặc trace chi tiết. Download trên frontend dùng chính JSON đã nhận, không cần thêm endpoint server.
