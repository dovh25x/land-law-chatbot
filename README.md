# Hà Nội · Pháp luật đất đai

Web chatbot tiếng Việt dùng FastAPI, LangGraph, Gemini, PostgreSQL/pgvector và React. Hai chế độ baseline/agentic dùng cùng nguồn dữ liệu và model. Agent chỉ có công cụ đọc với tham số định kiểu, giới hạn 6 lần gọi LLM, 12 công cụ, hai vòng retrieval và 90 giây. Chỉ phát câu trả lời qua SSE sau kiểm tra căn cứ; trace là sự kiện thực thi.

## Trạng thái

Website: https://hanoi-land-law.pages.dev; API: https://land-law-chatbot.onrender.com. Hạ tầng đã live và một lượt Gemini/SSE thật đã qua smoke. Corpus chưa công bố; đây chưa phải bản phát hành đã nghiệm thu M0–M6. Xem [bằng chứng và hạng mục còn mở](docs/IMPLEMENTATION_STATUS.md), [nguồn thật và khoảng trống](docs/SOURCES.md), [benchmark](docs/BENCHMARK.md). Không có câu trả lời hay chỉ số chất lượng giả trong runtime. SQLite dành cho phát triển; production bắt buộc PostgreSQL.

Preflight ngày 12/10/2026 (giờ Hà Nội): model được kế hoạch dự kiến `gemini-2.5-flash` trả HTTP 404; `gemini-3.5-flash-lite` gọi sinh JSON thật thành công và có Free tier theo [tài liệu Google](https://ai.google.dev/gemini-api/docs/pricing). Cấu hình hiện dùng model này cho cả hai chế độ; embedding giữ `gemini-embedding-2`, 768 chiều. Thay model phải chạy lại benchmark. Hệ thống không chuyển sang model khác khi hết quota.

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

Manifest `data/sources.json` chứa nguồn chính thức, checksum raw và metadata pháp lý đã rà soát. Chạy ingestion online hoặc offline với raw đã tải. PDF ảnh cần Tesseract `vie+eng` và Poppler trên máy ingestion; backend Docker không chứa OCR. Nguồn chưa duyệt, draft, shell tải dữ liệu, checksum thay đổi, OCR lỗi và hồ sơ cá nhân chưa ẩn danh đều bị cách ly.

```bash
.venv/bin/land-law migrate                 # PostgreSQL, quyền owner/admin
.venv/bin/land-law ingest --offline       # hoặc ingest --ocr để thu thập online
.venv/bin/land-law ingest --offline --embed
.venv/bin/land-law benchmark --split dev --release-id corpus-<id>
.venv/bin/land-law benchmark --split acceptance --release-id corpus-<id>
.venv/bin/land-law publish corpus-<id>
```

Embedding theo batch tối đa tám Content độc lập, một vector cho mỗi đoạn, checkpoint theo model/định dạng/title/checksum. Chạy lại tiếp tục checkpoint và không nhân đôi release cùng nội dung/metadata. `publish` từ chối khi thiếu nguồn bắt buộc (gồm QĐ 56/2024 lịch sử), độ bao phủ, metadata, embedding hoặc báo cáo nghiệm thu đã rà soát cho đúng release. Benchmark chạy được trên staging trước công bố; không cần bypass gate để đánh giá.

Bộ 120 câu hỏi gồm 40 dev/80 acceptance; căn cứ và rubric draft phải được đối chiếu toàn văn, bổ sung `gold_chunk_ids`, rồi review từng câu trả lời. Chỉ số chưa đo/rà soát hiển thị `null`; kết quả chưa đủ không được coi là đạt. Các ca benchmark là tình huống giả định, không phải hồ sơ người dân.

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
