# Vận hành MVP

## Tài khoản và cấu hình

Chỉ sử dụng gói Free. Chủ tài khoản tạo/xác minh tài khoản, cấp khóa trong `.env` hoặc GitHub Secrets, không gửi khóa qua chat. `.env.example` là danh sách cấu hình. Không bật billing, tự nâng cấp hoặc sử dụng backup trả phí. Quota của nhà cung cấp được kiểm tra bằng preflight và dashboard tài khoản; model xuất hiện trong danh sách không bảo đảm endpoint gọi được.

`DATABASE_URL` là Supabase pooler URL TLS, username có project reference; URL-encode password. Dùng owner cho migration/ingestion; production nên dùng login riêng được cấp role `landlaw_runtime` (RLS, chỉ đọc corpus, ghi phiên/trace/counter/cache). Không dùng service-role key trong frontend. `SUPABASE_SERVICE_ROLE_KEY` chỉ dành cho thao tác Storage ngoại tuyến, không cần đưa vào Render runtime.

`GEMINI_API_KEY`, `GEMINI_MODEL`, `EMBEDDING_MODEL`, `DATABASE_URL`, `IP_HASH_SECRET` ổn định, `CORS_ORIGINS` origin Cloudflare chính xác là các cấu hình backend. Production đặt `APP_ENV=production`; SQLite, TLS thiếu và CORS wildcard bị từ chối. Luôn giữ secret IP ít nhất 32 ký tự. Không thay đổi secret giữa các lần restart vì có thể phá vỡ bộ đếm nhóm IP.

## Triển khai miễn phí

1. Push repository đã scan secret và kiểm thử vào repository người dùng cung cấp. Dữ liệu raw, embedding, backup và `.env` không commit vào Git.
2. Supabase: `land-law migrate`, ingestion staging, benchmark và publish đúng release. Bucket `legal-corpus` riêng tư. Giữ database <350 MB, Storage <700 MB; dùng truy vấn dung lượng trước publish, giữ active/previous release và dọn staging cũ. Archive raw chính thức đã được rà soát; không upload draft hoặc bản chứa định danh chưa xử lý.
3. Render: tạo Web Service **Free**, Docker từ repository, region Singapore, một worker. `render.yaml` có blueprint. Health check `/healthz`; `/readyz` phải thành công riêng trước nghiệm thu. Cấu hình env như trên; `VITE_API_BASE_URL` chỉ là origin API công khai. Không disk bền vững trên Render.
4. Cloudflare Pages: tạo project Direct Upload Free, build `frontend`, thư mục `dist`. Cấu hình API Render HTTPS để CSP cho phép kết nối. Đặt origin Pages vào CORS backend. HTTPS nền tảng tự cấp.
5. `.env`: `RENDER_API_KEY`, `RENDER_SERVICE_ID`, `CLOUDFLARE_API_TOKEN` có quyền Pages đúng account, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_PAGES_PROJECT`, `VITE_API_BASE_URL`. Script chỉ deploy existing service và xác nhận plan=free trước deploy backend.

```bash
.venv/bin/python scripts/deploy.py backend
.venv/bin/python scripts/deploy.py frontend
.venv/bin/land-law smoke https://<service>.onrender.com
```

URL hiện tại: https://hanoi-land-law.pages.dev và https://land-law-chatbot.onrender.com. Trước khi có corpus công bố, chạy `.venv/bin/python scripts/smoke_infrastructure.py` để kiểm tra kết nối database, CORS, cách ly phiên, SSE/Gemini thật và lưu hội thoại. Script ghi `reports/infrastructure-smoke.json`, luôn giữ `acceptance_passed=false`; `/readyz` trả 503 vì thiếu corpus là trạng thái đúng ở giai đoạn này. Sau khi công bố phải chạy smoke pháp lý và nghiệm thu riêng.

Workflow deploy thủ công dùng GitHub environment `production`: Secrets `RENDER_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; Variables `RENDER_SERVICE_ID`, `CLOUDFLARE_PAGES_PROJECT`, `API_BASE_URL`. Secrets không xuất hiện trong bundle. Không coi deploy thành công là nghiệm thu khi corpus/benchmark chưa đạt.

## Quota, timeout và bảo vệ API

Mỗi phiên và nhóm IP: 3 lượt/phút, 20 lượt/ngày; toàn hệ thống tối đa hai lượt đang chạy. Bộ đếm dùng transaction SQL để không mất sau restart. API trả 429 với `Retry-After`; Gemini quota trả `limited`, timeout trả `error`. Mặc định tối đa 100 request LLM/ngày và 500 embedding request/ngày trong ứng dụng; batch tối đa tám vector/request. Retry tính vào bộ đếm. Đặt mức theo quota tài khoản thực tế, không tăng chỉ để che lỗi 429. Benchmark có checkpoint và có thể tiếp tục qua nhiều ngày trên cùng release/model/dataset.

Render Free có cold start; frontend báo trạng thái khởi động, cho thử lại, chờ tối đa ba phút gồm khởi động. p95 benchmark chỉ đo backend sẵn sàng và lượt không cache; cold start cần smoke đo riêng. Không bật ping để né chính sách miễn phí. Supabase Free có thể pause; `/readyz` trả 503 khi dependency chưa sẵn sàng.

Token phiên 256 bit, lưu hash phía server, trình duyệt `sessionStorage`; mỗi request lịch sử/trace cần Bearer token cùng phiên. Tự xóa sau bảy ngày. Cache chỉ của chính phiên, khóa có history/corpus/model/date/project/mode; không cache nội dung riêng sang phiên khác. Công cụ đọc schema định kiểu; model không mở URL/SQL/shell. Markdown bỏ raw HTML và không thực thi link người dùng. Tài liệu là dữ liệu không đáng tin, không có quyền điều khiển công cụ.

Ingress: `TRUST_PROXY_HEADERS=false` mặc định và Uvicorn `--no-proxy-headers`. Chỉ bật khi đã kiểm chứng Render ghi đè header. Khi không tin proxy, nhiều người có thể chia sẻ IP ingress và bị giới hạn chung; session vẫn có giới hạn riêng. Đây là lựa chọn bảo thủ cho demo nhỏ.

## Cập nhật nguồn và công bố

Workflow `corpus.yml` kiểm tra hằng ngày, tải vào staging, không tự đổi active. Raw checksum khác bản đã rà soát làm cách ly; kiểm tra lại toàn văn, số/ngày, tỷ lệ/số tiền, trạng thái hiệu lực và quan hệ từng điều. OCR sidecar phải có checksum PDF/OCR, đủ trang và review; không dựa vào việc chạy OCR thành công. Pending không được index. Mốc hiệu lực điều khoản khác ngày chung cần metadata `provision_validity`; quan hệ bãi bỏ một phần không bãi bỏ toàn văn.

Bộ dữ liệu công bố có ID bất biến và lưu chứng cứ benchmark đúng release. `land-law publish` backup trước đổi pointer. Corpus quá bảy ngày chưa kiểm tra nguồn không khẳng định tính hiện hành. Không coi một lần parse offline là lần kiểm tra nguồn mới.

## Backup, rollback, restore và lưu trữ

```bash
.venv/bin/land-law backup --output data/backups/manual.json
.venv/bin/land-law rollback
.venv/bin/land-law restore data/backups/manual.json
.venv/bin/land-law cleanup
```

Backup CLI chứa corpus và pointer active/previous, quyền tệp 0600; không chứa token phiên hoặc câu hỏi. PostgreSQL vẫn là nguồn bền vững cho lịch sử qua restart. Để khôi phục hội thoại sau mất database, đặt BACKUP_ENCRYPTION_KEY (Fernet), chạy `land-law backup --include-sessions --output data/backups/private.enc`; archive được mã hóa và restore giữ TTL bảy ngày. Giữ khóa tách biệt; không đưa plaintext hội thoại vào GitHub artifact. Backup mặc định chỉ khôi phục corpus. Sau restore chạy `/readyz`, truy vấn nguồn, smoke thật và kiểm tra cách ly phiên.

Workflow maintenance khi variable `MAINTENANCE_ENABLED=true`, secret admin DATABASE_URL: cleanup hằng ngày, backup định kỳ trước publish và hằng tuần; artifact tám ngày. Daily staging được nén tar.gz và giữ ba ngày để dự phòng dung lượng Actions miễn phí. Kiểm tra artifact không chứa định danh/secret; hội thoại chỉ có trong archive mã hóa. Storage upload riêng tư dùng `land-law upload <release.json>`. Restore rehearsal dùng database phát triển tách biệt để tránh ghi đè active production trong lúc kiểm tra.

## Theo dõi lỗi

Log JSON gồm request ID, status HTTP, model, latency, token/call counts và trace ID; không log nguyên câu hỏi, prompt, token phiên, DB URL hoặc provider response body. Trace UI chỉ là tên tool, tài liệu, thời gian và kết quả kiểm tra. `/healthz` kiểm tra process, `/readyz` kiểm tra database/corpus và cấu hình AI; smoke dùng Gemini thật để xác nhận dependency không chỉ có khóa.

Khi lỗi database, không phát câu trả lời là thành công trước khi lưu. Khi Gemini lỗi/429, không sinh trả lời giả hay chuyển sang API khác. Dùng Render log request/trace ID để đối chiếu, chạy preflight, khôi phục nguồn/kết nối, rồi smoke lại. Rollback app dùng image/deploy trước trong Render, frontend redeploy build đã kiểm thử; rollback corpus dùng pointer riêng.

## Tiếp tục embedding qua quota miễn phí

`land-law ingest --offline --cached-embeddings-only` tái sử dụng vector đã có, không gọi embedding API. `land-law ingest --offline --embed` tiếp tục các đoạn còn thiếu. Batch tám đoạn tính là tám input tại provider; ngoài giới hạn HTTP, `GLOBAL_DAILY_EMBEDDING_ITEM_LIMIT=900` chừa dự phòng cho query. Daily quota lấy RetryInfo của provider; không suy giờ reset từ timezone máy. Văn bản parse đạt nhưng thiếu vector vẫn ở staging và bị gate chặn publish.

Workflow `embeddings.yml` sử dụng private raw archive (`land-law restore-sources`), seed checkpoint trong Storage private và cache JSON checkpoint; `--no-persist` giữ bản trung gian trong artifact để tránh lấp database bằng nhiều staging release. Muốn chạy: Secrets ADMIN_DATABASE_URL, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY; repository variables EMBEDDING_RESUME_ENABLED=true và EMBEDDING_SEED_SHA256. Quota đạt thì lưu checkpoint và dừng gọi thêm; không tự công bố corpus. Sau khi embedding đầy đủ phải kiểm tra nguồn lại, review benchmark và publish qua CLI.

Operator chạy `python scripts/embedding_checkpoint_seed.py archive` để tạo seed bất biến trong Storage private; `restore` xác minh checksum, tên tệp và vector 768 chiều, không ghi đè checkpoint mới hơn. Lần triển khai này đã archive/restore đối chiếu 958 checkpoint thật. Không đưa vector vào Git. Seed là dữ liệu pháp luật công khai, không chứa hội thoại hoặc khóa API.

`pip install PyNaCl==1.6.2` chỉ trên máy operator, rồi `python scripts/configure_github.py`: cấu hình Secrets bằng sealed-box của GitHub và Variables, bật lịch sau khi đủ cấu hình. Token cần Secrets và Variables đọc/ghi. Script giới hạn repository đã được cấp quyền, không in giá trị secret; backend Docker không cần PyNaCl. Có thể dùng repository Secrets cho jobs environment `production` khi không đặt secret cùng tên tại environment.

`land-law archive-sources` lưu bản raw/checksum/manifest nguồn đã rà soát vào private Storage. Nội dung cùng tên chỉ được nhận nếu checksum khớp; staging database giữ dự phòng 350 MB và Storage 700 MB. `land-law restore-sources` xác minh checksum trước ghi.

Render service đã tạo: chạy `python scripts/configure_render.py` để xác nhận Free/Docker/repo, đặt runtime credentials và /healthz; chạy `python scripts/deploy.py backend`, rồi `frontend`. Backend chỉ có DATABASE_URL runtime; ADMIN_DATABASE_URL, Storage service role và khóa backup không đưa lên API. `frontend-preview` chỉ công bố giao diện với thông báo chưa có backend.

Đặt BACKUP_ENCRYPTION_KEY trong GitHub Secrets riêng biệt để workflow maintenance sao lưu hội thoại mã hóa; không có khóa thì workflow chỉ sao lưu corpus. Job cần MAINTENANCE_ENABLED=true. GitHub token quản trị phải có quyền Secrets đọc/ghi để cấu hình qua API; Contents/Workflows không tự cấp quyền này. Kiểm tra thực tế bằng `scripts/check_postgres.py`, `scripts/check_restore.py` và browser e2e.
