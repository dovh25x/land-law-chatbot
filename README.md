# Hanoi Land Law Assistant

Trợ lý tiếng Việt tra cứu pháp luật đất đai Hà Nội bằng Agentic RAG, kèm đoạn nguồn, thời điểm xem xét và trace thực thi để đối chiếu.

Website: https://hanoi-land-law.pages.dev · API: https://land-law-chatbot.onrender.com

## Phạm vi và hành vi

Tra cứu bồi thường, hỗ trợ, tái định cư và thông tin dự án Vành đai 4. Thư viện gồm snapshot 69 tài liệu và 7.610 vector; tài liệu dự án khác chỉ để tham khảo. Hệ thống hỗ trợ hỏi tiếp trong cùng phiên, mở nguồn theo điều/trang, nêu thiếu chứng cứ và hỏi bổ sung khi tình huống chưa đủ dữ kiện.

Bản thử nghiệm, chưa được thẩm định pháp lý độc lập. Không tiếp nhận hồ sơ cá nhân, tính tiền bồi thường hoặc xác định thửa đất bằng GIS. Nguồn không cập nhật tự động; kết luận còn phụ thuộc thời điểm và hồ sơ thực tế. Chỉ nhập thông tin đã ẩn danh. Hosting miễn phí có thể cần thời gian khởi động hoặc hết quota.

## Kiến trúc

Nguồn chính thức → parse/OCR ngoại tuyến → chia đoạn và metadata → E5 → corpus snapshot → hybrid retrieval → LangGraph → kiểm chứng → FastAPI/SSE → React.

React/TypeScript/Vite; FastAPI/LangGraph; Groq GPT-OSS 120B; E5 ONNX Q8 384 chiều; PostgreSQL/pgvector cloud và SQLite local. Hybrid search kết hợp từ khóa, vector, tiêu đề và viện dẫn bằng RRF. Agent chọn công cụ chỉ đọc, tổng hợp và kiểm tra trước khi phát đáp án. Kiểm tra kỹ thuật không bảo đảm mọi diễn giải pháp luật đều đúng.

## Chạy local

Python 3.12+ và Node 24. Cần internet tải E5, corpus và gọi Groq; SQLite không yêu cầu tài khoản database cloud.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
cp .env.example .env
```

Điền `GROQ_API_KEY`; giữ `DATABASE_URL` và `ADMIN_DATABASE_URL` trống, `APP_ENV=development`, `SQLITE_PATH=data/local.db`. Không đưa secret vào biến `VITE_*`.

Tải ba asset từ [corpus Release](https://github.com/dovh25x/land-law-chatbot/releases/tag/corpus-de584c31fc95f9a2) và kiểm tra checksum trước khi restore:

```bash
mkdir -p data/demo
curl -fL https://github.com/dovh25x/land-law-chatbot/releases/download/corpus-de584c31fc95f9a2/corpus-backup.json -o data/demo/corpus-backup.json
curl -fL https://github.com/dovh25x/land-law-chatbot/releases/download/corpus-de584c31fc95f9a2/manifest.json -o data/demo/manifest.json
curl -fL https://github.com/dovh25x/land-law-chatbot/releases/download/corpus-de584c31fc95f9a2/SHA256SUMS -o data/demo/SHA256SUMS
(cd data/demo && sha256sum -c SHA256SUMS)
```

Snapshot có 69 tài liệu/7.610 đoạn; manifest ghi corpus ID, commit gốc và fingerprint nguồn lúc đóng gói. Đây là bản phát hành dữ liệu; trạng thái ứng dụng được ghi riêng trong báo cáo.

```bash
.venv/bin/python backend/landlaw/local_embedding.py download models/e5
.venv/bin/land-law restore data/demo/corpus-backup.json
.venv/bin/uvicorn landlaw.api:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Restore vào SQLite mới, không dùng cấu hình database cloud đang phục vụ. Terminal khác:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Mở http://127.0.0.1:5173. Nếu dùng Docker Compose, vẫn phải chuẩn bị `.env` và restore corpus vào `data/local.db` trước khi chạy `docker compose up --build`.

## Đánh giá và hạn chế

[Báo cáo công bố](reports/latest.json) luôn gắn với corpus, model và fingerprint. Giao diện cảnh báo nếu báo cáo khác cấu hình đang chạy. Các kết quả chi tiết nằm trong `reports/`; báo cáo cũ không đại diện bản sửa mới.

Bộ hồi quy chính có 20 câu, cộng 4 câu kiểm tra bổ sung khóa riêng trước khi sửa prompt. Kết quả tách nhóm trả lời nội dung, hỏi làm rõ và thiếu chứng cứ/ngoài phạm vi. Tổng số đạt của suite không phải độ chính xác trả lời pháp luật. Citation khớp corpus chỉ xác nhận xuất xứ; chất lượng diễn giải cần rà soát theo nguồn. Bộ câu hỏi nhỏ chưa chứng minh khả năng tổng quát; không có so sánh để kết luận agentic vượt RAG thường.

SQLite và PostgreSQL dùng lexical search khác nhau; đánh giá retrieval ghi backend cụ thể. Độ trễ/token/số lần gọi là thống kê một lượt chạy, không phải SLA. Mốc kiểm tra corpus phải được giữ nguyên cho tới khi nguồn được kiểm tra lại thực sự.

## Phát triển

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm run test:e2e
```

Quy tắc sửa mã, kiểm thử, đánh giá, quản lý dữ liệu và triển khai được tập trung trong [AGENTS.md](AGENTS.md).
