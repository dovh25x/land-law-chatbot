# Vành đai 4 · Trợ lý pháp lý

Hỏi đáp tiếng Việt về bồi thường, hỗ trợ và tái định cư cho dự án Vành đai 4 tại Hà Nội. Mỗi kết luận cần có chứng cứ trong corpus và được kiểm tra trước khi trả lời. Tin dự án chỉ cung cấp bối cảnh; hệ thống không xác định thửa đất, tính tiền hoặc bảo đảm quyền lợi cá nhân.

Giao diện hội thoại, thư viện nguồn và chi tiết thực thi là ba cách kiểm tra kết quả. Hội thoại lưu tại trình duyệt trong 7 ngày, không đồng bộ thiết bị. Nội dung câu hỏi và ngữ cảnh được gửi tới Groq để xử lý; không nhập thông tin định danh hoặc hồ sơ riêng tư.

## Chạy local

Cần Python 3.12, Node.js 24 và khoảng 1 GiB dung lượng trống cho môi trường/model/corpus.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
cp .env.example .env
.venv/bin/python backend/landlaw/local_embedding.py download models/e5
cd frontend
npm ci
```

Điền `GROQ_API_KEY` trong `.env`. Local dùng SQLite: để trống `DATABASE_URL` và `ADMIN_DATABASE_URL`, đặt `SQLITE_PATH=data/ring4.db`. Không dùng credentials production cho quickstart.

Corpus một dự án đang được chuẩn bị phát hành: `corpus-581da76c79b0b362`. Chỉ sử dụng URL Release sau khi asset đã phát hành và khôi phục kiểm chứng; hiện chưa có liên kết tải được xác nhận cho phiên bản này. Có thể kiểm tra manifest trong `data/sources.json`; ingest lại không cần thiết nếu đã có snapshot phù hợp.

Khi có bộ asset `corpus-backup.json`, `manifest.json`, `SHA256SUMS`, đặt cùng thư mục và chạy:

```bash
sha256sum -c SHA256SUMS
DATABASE_URL='' ADMIN_DATABASE_URL='' SQLITE_PATH=data/ring4.db .venv/bin/land-law restore corpus-backup.json
.venv/bin/uvicorn landlaw.api:app --host 127.0.0.1 --port 8000
```

Trong terminal khác: `cd frontend && npm run dev`. Vite proxy phục vụ API local. Production dùng API cùng origin qua Cloudflare; không trỏ giao diện trực tiếp tới Render.

## Kiến trúc và đọc source

![Kiến trúc](docs/diagrams/architecture.svg)

FastAPI/LangGraph điều phối một pipeline plan → công cụ chỉ đọc → synthesis → verify. Groq GPT-OSS 120B sinh JSON; E5 ONNX Q8 384 chiều và hybrid retrieval tìm chứng cứ. SQLite phục vụ local; PostgreSQL/pgvector phục vụ cloud. Embedding của snapshot được giữ khi thu gọn corpus.

Bắt đầu từ [PRD](docs/PRD.md), [kiến trúc](docs/ARCHITECTURE.md), rồi [API](docs/API.md). [Mục lục tài liệu](docs/README.md) dẫn tới vận hành, thiết kế Figma, đánh giá và các ADR. `AGENTS.md` chỉ giữ ngữ cảnh phát triển ngắn.

## Kiểm tra và kết quả

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm run test:e2e
```

Unit/E2E dùng fixture; không chứng minh chất lượng model thật. Kết quả có phiên bản nằm tại [reports](reports/), API chỉ công bố `reports/latest.json` kèm kiểm tra fingerprint. Báo cáo cũ dùng corpus/cấu hình khác là bằng chứng lịch sử; không suy ra chất lượng phiên bản hiện hành. Không diễn giải tỷ lệ đạt gồm cả hỏi lại/từ chối thành độ chính xác pháp luật.

Giới hạn: corpus có coverage gaps, kiểm tra hiệu lực và verifier có thể bỏ sót; chưa có thẩm định pháp lý độc lập. Free hosting có cold start và hạn mức provider. Khi nguồn quá hạn, thiếu chứng cứ hoặc hết ngân sách, hệ thống phải công khai giới hạn thay vì suy đoán.
