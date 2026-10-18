# Runbook vận hành

## Mô hình triển khai và trách nhiệm

Ứng dụng sử dụng Cloudflare Pages/Function làm frontend và ingress, một worker Render Free chạy FastAPI, Supabase PostgreSQL/pgvector lưu corpus và metadata. Ingest, OCR và đóng gói corpus được thực hiện ngoại tuyến.

Người vận hành chịu trách nhiệm quản lý credentials, rà soát nguồn, phát hành corpus, kiểm tra deployment và xử lý sự cố. Hosting Free có cold start và giới hạn tài nguyên; các số đo một lần chạy không tạo thành SLA.

## Cấu hình và phân quyền

Tên biến tham chiếu tại [`.env.example`](../.env.example). Không đưa giá trị secret vào Git, tài liệu, log hoặc command line được chia sẻ.

| Nơi cấu hình | Biến chính | Nguyên tắc |
|---|---|---|
| Render | `APP_ENV`, `DATABASE_URL`, `GROQ_API_KEY`, `INGRESS_SECRET`, `IP_HASH_SECRET`, `TURNSTILE_SECRET_KEY`, `PUBLIC_HOSTNAME` | Database role runtime; không cấu hình owner credentials |
| Cloudflare Function | `BACKEND_ORIGIN`, `INGRESS_SECRET` | Origin backend cố định; secret ingress phải khớp Render |
| Frontend build | `VITE_API_BASE_URL`, `VITE_TURNSTILE_SITE_KEY` | Chỉ cấu hình công khai; API cùng origin Pages |
| Operator | `ADMIN_DATABASE_URL` và credentials triển khai khi cần | Quyền nâng cao chỉ dùng cho tác vụ được kiểm soát |
| GitHub Actions | Encrypted secrets và repository variables | Không lưu owner DB credential trong workflow runtime |

`Settings.for_operator()` ưu tiên `ADMIN_DATABASE_URL` khi biến này có giá trị. Trước migrate, restore hoặc publish, phải xác nhận database đích; không dùng cấu hình owner của production để thử lệnh khôi phục local.

Migration `006_browser_history.sql` xóa payload hội thoại cũ và thu hồi quyền runtime trên các bảng đó. Không tạo backup hội thoại trước hoặc sau migration.

## Kiểm tra tình trạng

```bash
curl --fail https://hanoi-land-law.pages.dev/readyz
curl --fail https://hanoi-land-law.pages.dev/api/v1/status
.venv/bin/land-law ops-status --check
```

- `/healthz` xác nhận tiến trình phản hồi.
- `/readyz` kiểm tra DB, cấu hình provider và corpus; không thực hiện generation thật.
- `/api/v1/status` phản ánh generation switch, freshness và cooldown của deployment.
- `ops-status` kiểm tra metadata DB, nguồn và usage; `--check` trả exit code lỗi khi cần chú ý. Giá trị cấu hình của CLI là cấu hình tiến trình operator, không thay thế status từ deployment.

Không dùng riêng HTTP status mở stream để đếm lượt chat thành công. Theo dõi sự kiện cuối `turn_finished`/`turn_failed` và `result.status`; metadata trạng thái transport có thể khác kết quả trả lời nội dung.

## Ingress và chống lạm dụng

Cloudflare ký method, path, query, timestamp, IP và SHA256 body bằng HMAC. Backend production kiểm tra chữ ký cùng cửa sổ 60 giây, không tin IP do client tự khai báo. API chỉ được gọi qua Pages; truy cập trực tiếp Render phải bị từ chối.

Turnstile được xác minh server-side khi tạo phiên, với hostname đã cấu hình và action `create_session`. Managed challenge có thể yêu cầu tương tác thủ công. Không dùng test key hoặc tắt xác minh production để làm smoke test đạt.

| Phạm vi | Giới hạn hiện tại |
|---|---|
| Hệ thống | Hai lượt đồng thời; một lượt đang chạy cho mỗi phiên |
| Chat theo phiên/IP | Ba request/phút cho mỗi loại định danh |
| Chat theo phiên | 20 request/ngày |
| Public LLM | 100 request/ngày, gồm retry |
| Public token usage | Dừng nhận thêm khi usage ghi nhận đạt 100.000 token/ngày |
| Body | 64 KiB; thời gian đọc body tối đa 10 giây |

Giới hạn public LLM/token được cấu hình bằng `PUBLIC_DAILY_LLM_LIMIT` và `PUBLIC_DAILY_TOKEN_LIMIT`. Ngưỡng token không phải trần tuyệt đối: request đang chạy hoặc lỗi không trả usage có thể làm số sử dụng thực tế khác counters.

API dùng scope `public`; CLI/dev entrypoint tin cậy dùng `operator`, ghi usage riêng và không tiêu ngân sách public. Cả hai vẫn tuân thủ giới hạn thực tế cùng `Retry-After` của Groq. Không xoay key hoặc retry liên tục để vượt provider limit.

## Rà soát nguồn và freshness

Nguồn quá bảy ngày hoặc receipt cho biết `changed`/`unavailable` chặn generation. Runtime hiện kiểm tra freshness của corpus một cách bảo thủ; một nguồn cần rà soát có thể ảnh hưởng toàn bộ chat, dù thư viện vẫn truy cập được.

Quy trình rà soát:

1. Xác định tài liệu và checksum trong active corpus.
2. Kiểm tra nội dung nguồn chính thức, mốc hiệu lực, văn bản sửa đổi/thay thế và điều khoản chuyển tiếp. URL trả HTTP thành công là chưa đủ.
3. Lập receipt nêu `document_id`, `checksum`, `checked_at`, `status`, `relation_review` và `evidence_urls` chính thức.
4. Ghi nhận bằng `.venv/bin/land-law review-source <receipt.json>` với quyền phù hợp. Schema và validation nằm trong `backend/landlaw/ops.py`.
5. Nếu nội dung thay đổi, chuẩn bị corpus mới; không đánh dấu `unchanged` hoặc sửa `checked_at` để vượt freshness.

Sau restore phải đánh giá lại freshness. Backup không tự chứng minh nguồn còn hiện hành và không thay thế receipt rà soát.

## Backup và khôi phục

Backup công khai chỉ chứa corpus và state công khai cần khôi phục, không chứa phiên, message, trace, credential hoặc model cache.

```bash
.venv/bin/land-law backup --output data/backups/ring4-public-corpus.json
.venv/bin/python scripts/package_release.py --help
```

Trước khi phát hành, chạy packager trên backup đã kiểm tra. Output gồm `corpus-backup.json`, `manifest.json`, `SHA256SUMS`; manifest ghi corpus ID, source commit, trạng thái working tree và hash nguồn. Working tree chưa sạch không được mô tả là release source đã commit đầy đủ.

Khôi phục local theo [README](../README.md#2-tải-và-khôi-phục-corpus). Với PostgreSQL:

1. Cấp cấu hình owner/runtime cho database dành riêng cho khôi phục.
2. Áp dụng migrations và restore corpus tại database đó.
3. Đối chiếu checksum, corpus ID, phạm vi nguồn, số tài liệu/chunk, embedding contract và các tham chiếu.
4. Kiểm tra runtime role đọc được corpus, không ghi được payload hội thoại; kiểm tra lease và truy xuất.
5. Ghi artifact và dọn tài nguyên tạm đúng phạm vi của lần chạy.

`scripts/verify_postgres_restore.py` dùng schema tạm. `scripts/verify_postgres_database.py` tạo database tạm riêng và cần quyền tạo database; script chỉ xóa database tạm do chính lần chạy tạo. Cả hai không phải lệnh restore đè database đang phục vụ.

Không coi backup hợp lệ chỉ vì file đã được tạo. Bằng chứng restore phải xác định rõ database/schema thử nghiệm và các bước đã kiểm tra.

## Phát hành corpus và rollback

Snapshot mới chỉ chuyển active sau khi kiểm tra phạm vi, tính toàn vẹn, Release download và restore riêng thành công. Không embedding lại chunk chỉ vì lọc dự án.

Corpus đa dự án cũ đã được thu hồi khỏi dữ liệu vận hành và asset Release; [bản ghi thu hồi](../reports/corpus-retirement.json) giữ phạm vi cùng digest. Giữ báo cáo và checksum lịch sử; khả năng tái lập bị giới hạn khi asset nguồn đã bị thu hồi.

Chỉ rollback tới corpus Vành đai 4 và code không lưu hội thoại lên server. Nếu chưa có bản rollback đáp ứng điều kiện, đặt `GENERATION_ENABLED=false` và giữ tra cứu nguồn.

## Triển khai và xác minh

![Triển khai và phục hồi](diagrams/deploy-recovery.svg)

1. Chọn source SHA đã kiểm thử, push source và kiểm tra CI.
2. Xác nhận runtime role, biến môi trường, ingress secret và Turnstile hostname. Không thay đổi gói hosting trong bước deploy.
3. Dùng workflow triển khai hoặc `scripts/deploy.py`; ghim đúng SHA và không chạy các deploy cạnh tranh nhau.
4. Kiểm tra SHA thực tế trên Render, corpus, model và fingerprint qua API.
5. Kiểm tra nguồn và navigation trên desktop/mobile; sau đó kiểm tra luồng chat thật, hỏi tiếp, nguồn/trace tại client, reload, xóa và quyền truy cập phiên.
6. Ghi rõ phần đạt, lỗi và phần chưa xác minh trong artifact.

```bash
node scripts/verify_live_ui.mjs
node scripts/verify_live_ui.mjs --chat
```

Lệnh đầu chỉ kiểm tra navigation/nguồn, không chứng minh LLM hoạt động. Luồng `--chat` có thể bị chặn bởi Turnstile yêu cầu tương tác hoặc quota provider; kết quả đó phải giữ trạng thái chưa xác minh. Không dùng source-only hoặc CLI generation để thay thế tuyên bố đã kiểm tra toàn bộ public browser flow.

## Xử lý sự cố

| Triệu chứng | Kiểm tra ưu tiên | Hành động |
|---|---|---|
| `403 untrusted_ingress` | Cùng secret, origin, timestamp và đường gọi qua Pages | Sửa cấu hình; giữ backend từ chối direct API |
| Challenge không hoàn tất | Widget, hostname/action, secret và tương tác được yêu cầu | Hướng dẫn xác minh; không bypass |
| Chat unavailable, nguồn vẫn mở | Status generation, freshness, cooldown | Xử lý đúng lý do; không retry liên tục |
| `409` | Request ID đã dùng hoặc phiên đang chạy | Chờ kết thúc/lease; không replay tự động |
| Mất stream | Sự kiện cuối, timeout và metadata request | Thông báo không có server replay; người dùng quyết định lượt mới |
| Báo cáo không khớp | Corpus, model, backend và fingerprint | Giữ cảnh báo; đánh giá cấu hình mới khi phù hợp |
| Không lưu được lịch sử | IndexedDB, dung lượng hoặc quyền trình duyệt | Giữ nội dung trong tab và thông báo; không lưu server |

## Log, cleanup và provider data

Log JSON chỉ chứa metadata vận hành; không ghi câu hỏi, đáp án, history hoặc credentials. Dùng HTTP request ID để đối chiếu thay vì sao chép nội dung hội thoại vào ticket/log.

`.venv/bin/land-law cleanup` dọn metadata hết hạn. Workflow operations chạy theo lịch mỗi giờ; lỗi workflow được thông báo theo cấu hình notification GitHub của người vận hành. Đây không phải hệ thống cảnh báo hoặc SLA hoàn chỉnh.

Nội dung đi qua Cloudflare/Render tới Groq. Operator phải kiểm tra chính sách và cấu hình data controls của tổ chức tại provider trước khi khẳng định Zero Data Retention; repository không chứng minh được setting tài khoản đó. Lịch sử dài hạn chỉ ở client không phải cam kết nội dung không được xử lý bên ngoài thiết bị.
