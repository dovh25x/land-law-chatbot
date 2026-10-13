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

Mỗi phiên và nhóm IP: 3 lượt/phút, 20 lượt/ngày; toàn hệ thống tối đa hai lượt đang chạy. Bộ đếm dùng transaction SQL để không mất sau restart. API trả 429 với `Retry-After`; quota provider trả `limited`, timeout trả `error`. Không còn trần LLM/embedding theo ngày do ứng dụng đặt: bộ đếm `usage:*` chỉ ghi nhận, không chặn request. CLI ingestion/benchmark không chịu giới hạn chat phiên/IP. Giữ điểm dừng mỗi lượt: 6 lần gọi LLM (kể cả retry), 12 công cụ, hai vòng retrieval, 90 giây. Retry tạm thời tối đa ba lần và tuân thủ provider; quota dài hạn lưu checkpoint rồi dừng. Không chuyển sang API có phí.

Render Free có cold start; frontend báo trạng thái khởi động, cho thử lại, chờ tối đa ba phút gồm khởi động. p95 benchmark chỉ đo backend sẵn sàng và lượt không cache; cold start cần smoke đo riêng. Không bật ping để né chính sách miễn phí. Supabase Free có thể pause; `/readyz` trả 503 khi dependency chưa sẵn sàng.

Token phiên 256 bit, lưu hash phía server, trình duyệt `sessionStorage`; mỗi request lịch sử/trace cần Bearer token cùng phiên. Tự xóa sau bảy ngày. Cache chỉ của chính phiên, khóa có history/corpus/model/date/project/mode; không cache nội dung riêng sang phiên khác. Công cụ đọc schema định kiểu; model không mở URL/SQL/shell. Markdown bỏ raw HTML và không thực thi link người dùng. Tài liệu là dữ liệu không đáng tin, không có quyền điều khiển công cụ.

Ingress: `TRUST_PROXY_HEADERS=false` mặc định và Uvicorn `--no-proxy-headers`. Chỉ bật khi đã kiểm chứng Render ghi đè header. Khi không tin proxy, nhiều người có thể chia sẻ IP ingress và bị giới hạn chung; session vẫn có giới hạn riêng. Đây là lựa chọn bảo thủ cho demo nhỏ.

## Cập nhật nguồn và công bố

Workflow `corpus.yml` kiểm tra hằng ngày, tải vào staging, không tự đổi active. Raw checksum khác bản đã rà soát làm cách ly; kiểm tra lại toàn văn, số/ngày, tỷ lệ/số tiền, trạng thái hiệu lực và quan hệ từng điều. OCR sidecar phải có checksum PDF/OCR, đủ trang và review; không dựa vào việc chạy OCR thành công. Pending không được index. Mốc hiệu lực điều khoản khác ngày chung cần metadata `provision_validity`; quan hệ bãi bỏ một phần không bãi bỏ toàn văn.

Bộ dữ liệu công bố có ID bất biến và lưu chứng cứ benchmark đúng release. `land-law publish` backup trước đổi pointer. Corpus quá bảy ngày chưa kiểm tra nguồn không khẳng định tính hiện hành. Không coi một lần parse offline là lần kiểm tra nguồn mới.

`land-law benchmark --split smoke --release-id <id>` chạy 20 ca đã đối chiếu nguồn ở hai chế độ, tối đa hai lượt đồng thời. Review từng kết quả trong `data/evaluation/smoke-reviews.json` bằng khóa `<case>:<mode>:<sha256(result JSON sorted)>`, lưu `passed`, `source_checked`, `notes`, và một giá trị `claim_support` cho từng `verified_claims`. Gắn `reports/source-audit.json` và `reports/runtime-tests.json` đúng release/configuration, rồi chạy lại benchmark để tổng hợp. `land-law publish <id> --profile demo` chỉ qua khi đủ vector, 30 legal/5 nguồn mỗi dự án, cả 40 kết quả được review và mọi ca trọng yếu đạt. Demo công khai coverage gaps, chưa nghiệm thu. Lệnh publish mặc định `accepted` vẫn đòi bộ 80 acceptance và nguồn bắt buộc đầy đủ; không có tùy chọn force. Báo cáo smoke không bao giờ được xem là nghiệm thu 80 câu.

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

`land-law ingest --offline --cached-embeddings-only` tái sử dụng vector đã có, không gọi embedding API. `land-law ingest --offline --embed` tiếp tục các đoạn còn thiếu. Batch tám đoạn, bắt đầu hai batch đồng thời và tăng đến tám khi ổn định, giảm khi throttling; checkpoint ngay mỗi batch thành công. Daily quota lấy RetryInfo của provider; không suy giờ reset từ timezone máy. Văn bản parse đạt nhưng thiếu vector vẫn ở staging và bị gate chặn publish.

Workflow `corpus.yml` khôi phục raw và OCR đã được kiểm tra checksum từ Storage private trước khi tải nguồn hiện tại. Job dùng environment `production` và Secrets SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY; không nhận khóa database hoặc gọi AI. Nội dung tải mới phải khớp checksum đã rà soát; thay đổi được cách ly để review, không tái sử dụng OCR cũ cho PDF khác. `--no-persist` chỉ tạo artifact staging, không đổi release công khai.

Workflow `embeddings.yml` sử dụng private raw archive (`land-law restore-sources`), seed checkpoint trong Storage private và cache JSON checkpoint; `--no-persist` giữ bản trung gian trong artifact để tránh lấp database bằng nhiều staging release. Muốn chạy: Secrets ADMIN_DATABASE_URL, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY; repository variables EMBEDDING_RESUME_ENABLED=true và EMBEDDING_SEED_SHA256. Quota đạt thì lưu checkpoint và dừng gọi thêm; không tự công bố corpus. Sau khi embedding đầy đủ phải kiểm tra nguồn lại, review benchmark và publish qua CLI.

Operator chạy `python scripts/embedding_checkpoint_seed.py archive` để tạo seed bất biến chia shard nhỏ trong Storage private; `restore` xác minh manifest/shard checksum, tên tệp và vector 384/768/1024 chiều, không ghi đè checkpoint mới hơn. Không đưa vector vào Git. Seed là dữ liệu pháp luật công khai, không chứa hội thoại hoặc khóa API. Giới hạn giải nén tổng cộng 180 MB, tối đa 20.000 checkpoint.

Các corpus BGE cũ dùng `EMBEDDING_PROVIDER=cloudflare`, `EMBEDDING_MODEL=@cf/baai/bge-m3`, `EMBEDDING_DIMENSIONS=1024`, `CLOUDFLARE_ACCOUNT_ID` và token riêng `CLOUDFLARE_AI_API_TOKEN`. Provider sinh do `LLM_PROVIDER` chọn Gemini hoặc Qwen dự phòng; chỉ công bố sau gate trên đúng lựa chọn. Không đổi token Pages. Migration 004 giữ vector Gemini 768 và tạo index riêng 1024. Query chọn contract từ release đang hoạt động, kể cả rollback; không trộn vector khác model/chiều. Workers AI secret/embedding variables được cấu hình qua script GitHub. Nội dung bảng giữ dòng, tiêu đề, đơn vị và phân cách cột; bỏ padding PDF thừa, luôn đối chiếu trang gốc khi đọc giá.

Workflow `recovery.yml` sao lưu mã hóa thật, restore toàn bộ vào PostgreSQL/pgvector trên runner độc lập, kiểm tra cả ba chiều 384/768/1024, dữ liệu, rollback, thu hồi bản đầu và restart; chỉ upload báo cáo không chứa hội thoại. Cần secrets ADMIN_DATABASE_URL và BACKUP_ENCRYPTION_KEY. Nó không đổi pointer corpus production.

`pip install PyNaCl==1.6.2` chỉ trên máy operator, rồi `python scripts/configure_github.py`: cấu hình Secrets bằng sealed-box của GitHub và Variables, bật lịch sau khi đủ cấu hình. Token cần Secrets và Variables đọc/ghi. Script giới hạn repository đã được cấp quyền, không in giá trị secret; backend Docker không cần PyNaCl. Có thể dùng repository Secrets cho jobs environment `production` khi không đặt secret cùng tên tại environment.

`land-law archive-sources` lưu bản raw/checksum/manifest nguồn đã rà soát vào private Storage. Nội dung cùng tên chỉ được nhận nếu checksum khớp; staging database giữ dự phòng 350 MB và Storage 700 MB. `land-law restore-sources` xác minh checksum trước ghi.

Render service đã tạo: chạy `python scripts/configure_render.py` để xác nhận Free/Docker/repo, đặt runtime credentials và /healthz; chạy `python scripts/deploy.py backend`, rồi `frontend`. Backend chỉ có DATABASE_URL runtime; ADMIN_DATABASE_URL, Storage service role và khóa backup không đưa lên API. `frontend-preview` chỉ công bố giao diện với thông báo chưa có backend.

Đặt BACKUP_ENCRYPTION_KEY trong GitHub Secrets riêng biệt để workflow maintenance sao lưu hội thoại mã hóa; không có khóa thì workflow chỉ sao lưu corpus. Job cần MAINTENANCE_ENABLED=true. GitHub token quản trị phải có quyền Secrets đọc/ghi để cấu hình qua API; Contents/Workflows không tự cấp quyền này. Kiểm tra thực tế bằng `scripts/check_postgres.py`, `scripts/check_restore.py` và browser e2e.

## Provider sinh dự phòng được cho phép

Đặt `LLM_PROVIDER=cloudflare`, `CLOUDFLARE_LLM_MODEL=@cf/qwen/qwen3-30b-a3b-fp8`, account ID và token Workers AI. Gemini vẫn chọn được bằng `LLM_PROVIDER=gemini`; không tự chuyển provider trong một lượt. Qwen dùng JSON schema, Pydantic kiểm tra lại phía server và cùng verifier/chứng cứ như Gemini. Chỉ lấy nội dung trả lời, không lưu/phát reasoning của provider. Report/cache gắn đúng model và fingerprint; đổi provider cần chạy lại gate. Dùng `scripts/configure_render.py` để đồng bộ backend; không đặt token AI trong frontend.

HTTP 429 Workers AI code 3036, hoặc thông báo daily allocation/neurons dù mã khác, là hết phân bổ miễn phí theo ngày; 3040 là capacity tạm thời. Ưu tiên `Retry-After`; khi xác định daily allocation mà không có header, báo thời gian đến chu kỳ reset UTC theo tài liệu Cloudflare. Bộ đếm `usage:workers-ai-millineurons:*` chỉ quan sát, không chặn API. Không nâng Workers Paid hoặc bật billing.

`archive-sources` và `restore-sources` giữ cả parser input và các snapshot gốc của nguồn đã chuẩn hóa. Corpus lớn dùng phần gzip nhị phân tối đa 20 MB, manifest và checksum; `restore-archive` xác minh mọi phần và nội dung mở rộng rồi ghi tệp, không đổi pointer công khai. Checkpoint seed chia shard để tránh giới hạn 50 MB mỗi object Free.

Để dọn database khi có nhiều staging chưa công bố: `land-law retire-staging corpus-<old> ...`. Lệnh tạo backup đầy đủ có hội thoại mã hóa trước khi xóa, từ chối release active/previous hoặc có hồ sơ công bố, rồi VACUUM FULL các bảng corpus qua kết nối operator. Giữ hai release gần nhất và backup riêng; không dọn khi đang phát hành/đánh giá. Chạy trong khoảng bảo trì vì VACUUM khóa bảng corpus. Hội thoại và pointer không bị xóa. Không đưa quyền owner vào Render.

## OCR ngoại tuyến và kiểm tra bố cục

Cài Tesseract và gói ngôn ngữ `vie` miễn phí trên máy operator; `pip install -e ".[ocr]"` cài PDFium/Pillow cho script ngoại tuyến. Chạy `python scripts/ocr_offline.py source.pdf data/raw/source-unreviewed.ocr.txt --workers 2`. Script từ chối ghi đè, lưu text phân trang và JSON diagnostics; kết quả luôn pending cho đến khi đọc ảnh gốc và cập nhật checksum/review. Confidence cao không bảo đảm số tiền, dấu phủ định hoặc ngày đúng.

Với bảng xoay hoặc phân số, không chỉ dựa vào số ký tự text. Giữ PDF/ảnh gốc, lưu bản chuẩn hóa theo trang, hồ sơ vị trí đã đối chiếu và mọi checksum trong `source_artifacts`/`ocr_sidecars`. Các trang text không sửa giữ nguyên; trường hợp không kiểm tra được phải cách ly. `archive-sources` lưu cả bản gốc và sidecar verified. Không đưa Tesseract, Pillow hoặc PDFium vào backend Render.

Bộ nghiệm thu được khóa bằng `data/evaluation/acceptance-freeze.json`; chạy `python scripts/validate_benchmark_sources.py --release <release-file>` trước benchmark để kiểm tra gold khớp corpus. Đây là kiểm tra tính nhất quán, không tự chấm câu trả lời hoặc cấp chứng nhận pháp lý.

Khi nhiều model làm seed tổng vượt 180 MB, chạy `python scripts/embedding_checkpoint_seed.py archive <release-file>` để lưu riêng checkpoint của release đầy đủ. Mỗi vector phải khớp model/chiều/nội dung trong release; cache model khác vẫn giữ ở local và corpus archive. `EMBEDDING_CONCURRENCY` mặc định2, tối đa8; tăng sau các batch ổn định, giảm khi throttling và giữ mức ổn định giữa các tài liệu. Không phải trần request theo ngày.

E5 CPU đã bổ sung: `EMBEDDING_PROVIDER=local_onnx`, `EMBEDDING_MODEL=multilingual-e5-small-onnx-q8-window-v1`, `EMBEDDING_DIMENSIONS=384`. Docker tải và kiểm checksum model lúc build; runtime dùng `models/e5` và một encoder/khóa tuần tự cho hai lượt chat. Migration005 giữ index 768/1.024. Import Colab qua `scripts/import_colab_embeddings.py` chỉ tạo checkpoint, sau đó ingestion cached/offline tạo release mới; không tự publish. Query embedding lấy contract từ release đang hoạt động, kể cả rollback. CI chạy image với giới hạn cứng 512 MB và reserve RAM trước deploy.

Groq Free được chủ dự án cho phép: đặt `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-120b` (hoặc model trong allowlist). Không tự chuyển model/provider trong một lượt. Transport dùng strict JSON Schema, không có built-in tools, không phát reasoning; Pydantic và verifier nguồn tiếp tục kiểm tra. HTTP413 báo request quá lớn, HTTP429 tuân thủ Retry-After. Ngữ cảnh Groq chọn các đoạn nguyên vẹn trong giới hạn dung lượng, không cắt điều khoản; candidate bị bỏ không nằm trong danh sách citation được model chọn. Catalogue gọn và source spans tránh truyền văn bản trùng. Nội dung corpus chung đứng trước câu hỏi/lịch sử để hỗ trợ prefix cache của provider; câu trả lời riêng vẫn chỉ cache theo phiên.

`evaluation.yml` chạy checkpoint baseline/agentic trên cùng cấu hình ở GitHub runner miễn phí, không publish hoặc tự chấm đạt. Job dùng secret DATABASE_URL **role runtime**; unit test gỡ cấu hình operator và fixture luôn dùng SQLite tạm. ADMIN_DATABASE_URL chỉ dành cho migration, backup/restore hoặc thao tác operator đã được cấp quyền. Download artifact `legal-evaluation-evidence`, giữ nguyên run ID/configuration/attempt history, review từng kết luận đối chiếu nguồn rồi chạy lại summarise. Không ghép report hai cấu hình.
