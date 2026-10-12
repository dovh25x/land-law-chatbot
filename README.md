# Hà Nội · Pháp luật đất đai

Web chatbot tiếng Việt dùng FastAPI, LangGraph, Gemini, PostgreSQL/pgvector và React. Hai chế độ baseline/agentic dùng cùng nguồn dữ liệu và model. Agent chỉ có công cụ đọc với tham số định kiểu, giới hạn 6 lần gọi LLM, 12 công cụ, hai vòng retrieval và 90 giây. Chỉ phát câu trả lời qua SSE sau kiểm tra căn cứ; trace là sự kiện thực thi.

## Trạng thái

Website: https://hanoi-land-law.pages.dev; API: https://land-law-chatbot.onrender.com. Hạ tầng đã live và một lượt Gemini/SSE thật đã qua smoke. Corpus chưa công bố; đây chưa phải bản phát hành đã nghiệm thu M0–M6. Xem [bằng chứng và hạng mục còn mở](docs/IMPLEMENTATION_STATUS.md), [nguồn thật và khoảng trống](docs/SOURCES.md), [benchmark](docs/BENCHMARK.md). Không có câu trả lời hay chỉ số chất lượng giả trong runtime. SQLite dành cho phát triển; production bắt buộc PostgreSQL.

Provider sinh được chọn rõ bằng `LLM_PROVIDER`: Gemini hoặc Cloudflare Workers AI `@cf/qwen/qwen3-30b-a3b-fp8`. Qwen là dự phòng miễn phí được chủ dự án cho phép khi các model Gemini nhanh trả quota theo ngày. Hai chế độ dùng cùng model; cấu hình/provider có fingerprint riêng và không ghép kết quả đánh giá. Corpus mới `corpus-1cd1aa2da9050e47` có 52 tài liệu, 37 văn bản pháp lý và 5 nguồn mỗi dự án; đã có 4.636/5.582 vector BGE-M3 1.024 chiều. Còn 946 vector cần tiếp tục khi quota provider phục hồi. Bản BGE trước có đủ 5.149 vector vẫn được giữ làm staging. Chưa công bố corpus hoặc đạt gate demo. Không có trần gọi API theo ngày do ứng dụng đặt; giữ điểm dừng workflow và chống lạm dụng website. Không bật billing hoặc nâng gói.

## Chạy phát triển

Yêu cầu Python 3.12+, Node 24. Có thể đọc giao diện khi chưa cấu hình AI/corpus; trạng thái chưa sẵn sàng được hiển thị rõ.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
cp .env.example .env
# Điền GEMINI_API_KEY; DATABASE_URL để trống nếu dùng SQLite phát triển.
.venv/bin/land-law preflight --live
.venv/bin/uvicorn landlaw.api:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal thứ hai:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Mở http://127.0.0.1:5173. Vite proxy `/api`, `/healthz`, `/readyz` đến backend. Đặt `VITE_API_BASE_URL` khi build hosting tĩnh. Không đặt bất kỳ secret nào vào biến `VITE_*`.

## Corpus và phát hành

Manifest `data/sources.json` chứa nguồn chính thức, checksum raw và metadata pháp lý đã rà soát. Chạy ingestion online hoặc offline với raw đã tải. PDF ảnh xử lý ngoại tuyến bằng Tesseract tiếng Việt; `scripts/ocr_offline.py` dùng PDFium và lưu text phân trang cùng diagnostics. Cài tùy chọn `pip install -e ".[ocr]"` trên máy ingestion, không cài OCR vào backend Docker. Nguồn chưa duyệt, draft, shell tải dữ liệu, checksum thay đổi, OCR lỗi và hồ sơ cá nhân chưa ẩn danh đều bị cách ly.

```bash
.venv/bin/land-law migrate                 # PostgreSQL, quyền owner/admin
.venv/bin/land-law ingest --offline       # hoặc ingest --ocr để thu thập online
.venv/bin/land-law ingest --offline --embed
.venv/bin/land-law benchmark --split dev --release-id corpus-<id>
.venv/bin/land-law benchmark --split acceptance --release-id corpus-<id>
.venv/bin/land-law publish corpus-<id>
# Demo sớm: chỉ sau khi source audit/runtime tests và 20 ca smoke ở cả hai chế độ qua review
.venv/bin/land-law benchmark --split smoke --release-id corpus-<id>
.venv/bin/land-law publish corpus-<id> --profile demo
```

Embedding theo batch tối đa tám Content độc lập, một vector cho mỗi đoạn, checkpoint theo model/định dạng/title/checksum. Chạy lại tiếp tục checkpoint và không nhân đôi release cùng nội dung/metadata. `publish` từ chối khi thiếu nguồn bắt buộc (gồm QĐ 56/2024 lịch sử), độ bao phủ, metadata, embedding hoặc báo cáo nghiệm thu đã rà soát cho đúng release. Benchmark chạy được trên staging trước công bố; không cần bypass gate để đánh giá.

Bộ 120 câu hỏi gồm 40 dev/80 acceptance đã có rubric theo nguồn và 93 đoạn tham chiếu; 80 câu nghiệm thu được đóng băng trước chạy đánh giá cuối. Đây là rà soát nguồn của AI engineer, chưa được chuyên gia pháp lý thẩm định độc lập. Từng câu trả lời thật vẫn phải được chấm riêng. `scripts/validate_benchmark_sources.py` kiểm tra checksum/freeze và đối chiếu corpus, không tự chứng nhận độ chính xác pháp lý. Chỉ số chưa đo/rà soát hiển thị `null`; kết quả chưa đủ không được coi là đạt. Các ca benchmark là tình huống giả định, không phải hồ sơ người dân.

## Kiểm tra

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm audit
```

GitHub Actions kiểm tra Python 3.12, build web, audit và build Docker. Thu thập nguồn hằng ngày chỉ tạo staging. Lịch Actions không đảm bảo cập nhật thời gian thực.

## Vận hành và bàn giao

[Hướng dẫn triển khai, quota, cập nhật và khôi phục](docs/OPERATIONS.md), [kịch bản demo](docs/DEMO.md). Hosting mục tiêu: Cloudflare Pages Free, Render Free một worker, Supabase Free. Secret ở backend/.env/GitHub Secrets; trình duyệt chỉ gọi API. Không bật thanh toán hoặc nâng gói. Không nhận upload hồ sơ cá nhân, tính tiền tự động hoặc tra cứu GIS từng thửa.
