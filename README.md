# Vành đai 4 · Trợ lý pháp lý

Ứng dụng tra cứu bằng tiếng Việt về bồi thường, hỗ trợ và tái định cư cho dự án Vành đai 4 tại Hà Nội. Hệ thống kết hợp nguồn pháp luật và hồ sơ dự án có xuất xứ với một pipeline Agentic RAG; kết luận chỉ được phát sau bước kiểm chứng.

[Ứng dụng](https://hanoi-land-law.pages.dev) · [Tài liệu](docs/README.md) · [Kiến trúc](docs/ARCHITECTURE.md) · [Đánh giá](docs/EVALUATION.md)

## Khả năng và phạm vi

- Tra cứu quy định, điều kiện áp dụng, mốc hiệu lực và quan hệ sửa đổi hoặc thay thế văn bản.
- Hỏi tiếp theo ngữ cảnh hội thoại; mở nguồn, điều khoản, trang và đoạn trích của câu trả lời.
- Xem các bước thực thi quan sát được để đối chiếu quá trình tra cứu.
- Tra cứu thư viện nguồn độc lập với chức năng sinh câu trả lời.
- Lưu và xóa hội thoại trên thiết bị; hỗ trợ giao diện sáng, tối và màn hình nhỏ.

Phạm vi vận hành chỉ gồm Vành đai 4 và luật chung liên quan. Thông tin tổng quan dự án không xác định thửa đất, số tiền bồi thường hoặc quyền lợi của một hộ cụ thể. Sản phẩm đang ở trạng thái **bản thử nghiệm**, chưa có thẩm định pháp lý độc lập.

Hội thoại được lưu trong trình duyệt tối đa 7 ngày, không đồng bộ thiết bị. Khi gửi câu hỏi, nội dung và ngữ cảnh cần thiết được truyền tới backend và Groq để xử lý. Không nhập thông tin định danh hoặc hồ sơ riêng tư. Xem [ranh giới dữ liệu](docs/ARCHITECTURE.md#lưu-trữ-và-quyền-riêng-tư).

## Khởi chạy local

### 1. Chuẩn bị môi trường

Sử dụng Python 3.12 và Node.js 24. Các lệnh bên dưới chạy từ thư mục gốc repository, trừ khi có chỉ dẫn khác.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
npm --prefix frontend ci
cp .env.example .env
.venv/bin/python backend/landlaw/local_embedding.py download models/e5
```

Trong `.env`, cấu hình `GROQ_API_KEY`, giữ `APP_ENV=development`, để trống `DATABASE_URL` và `ADMIN_DATABASE_URL`, đặt `SQLITE_PATH=data/ring4.db`. Model E5 được tải riêng và xác minh checksum; không cần chạy lại embedding của corpus phát hành.

### 2. Tải và khôi phục corpus

Tải `corpus-backup.json`, `manifest.json` và `SHA256SUMS` từ [corpus Release](https://github.com/dovh25x/land-law-chatbot/releases/tag/corpus-581da76c79b0b362). Snapshot này chứa 59 tài liệu và 7.555 chunk, không chứa hội thoại hoặc model cache.

Đặt ba asset tại thư mục gốc repository, rồi chạy:

```bash
sha256sum -c SHA256SUMS
DATABASE_URL='' ADMIN_DATABASE_URL='' SQLITE_PATH=data/ring4.db .venv/bin/land-law restore corpus-backup.json
```

Chỉ restore vào database local mới hoặc database dành riêng cho việc khôi phục. Quy trình PostgreSQL và kiểm tra toàn vẹn được mô tả trong [vận hành](docs/OPERATIONS.md#backup-và-khôi-phục).

### 3. Chạy backend và frontend

Terminal thứ nhất:

```bash
.venv/bin/uvicorn landlaw.api:app --host 127.0.0.1 --port 8000
```

Terminal thứ hai:

```bash
npm --prefix frontend run dev
```

Mở địa chỉ Vite in trong terminal. Vite chuyển tiếp `/api` và `/readyz` tới backend local. OpenAPI có tại `http://127.0.0.1:8000/docs` trong môi trường development.

Nguồn quá hạn hoặc giới hạn thực tế của Groq có thể ngăn sinh câu trả lời dù ứng dụng khởi động thành công. Kiểm tra `/api/v1/status`; không tự đổi ngày kiểm tra nguồn để vượt điều kiện này.

## Kiến trúc tổng quan

![Kiến trúc hệ thống](docs/diagrams/architecture.svg)

React/Vite giao tiếp với FastAPI qua Cloudflare Pages Function. Backend chạy một graph plan → retrieval/tools → synthesis → verify, dùng Groq GPT-OSS 120B và E5 ONNX Q8 384 chiều. SQLite hỗ trợ local; PostgreSQL/pgvector phục vụ deployment. Ingest và OCR thực hiện ngoài runtime phục vụ chat.

| Thư mục | Trách nhiệm |
|---|---|
| `backend/landlaw/` | API, điều phối agent, retrieval, provider và lưu trữ |
| `frontend/` | Giao diện, lịch sử tại trình duyệt và proxy Cloudflare |
| `data/` | Manifest nguồn, quan hệ văn bản và các bộ câu hỏi đã khóa |
| `migrations/` | Schema và phân quyền PostgreSQL |
| `scripts/` | Đánh giá, đóng gói corpus, triển khai và xác minh |
| `docs/` | Yêu cầu sản phẩm, thiết kế hệ thống, contract và ADR |
| `reports/` | Artifact đánh giá và kiểm tra có phiên bản |

Bắt đầu với [PRD](docs/PRD.md), sau đó đọc [kiến trúc](docs/ARCHITECTURE.md) và [API](docs/API.md). Hướng dẫn dành cho coding agent nằm trong [AGENTS.md](AGENTS.md).

## Kiểm tra và đánh giá

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Unit test và E2E dùng fixture để kiểm tra hành vi phần mềm. Đánh giá chất lượng model được thực hiện riêng trên các bộ câu hỏi đã khóa; phương pháp, mẫu số và quy tắc công bố nằm tại [hướng dẫn đánh giá](docs/EVALUATION.md).

[Báo cáo có phiên bản](reports/evaluation/ring4-c4f0c661/README.md) ghi rõ các ca chưa đáp ứng yêu cầu. API công bố `reports/latest.json` kèm trạng thái khớp corpus và fingerprint. Kết quả SQLite không được trình bày như kết quả PostgreSQL; tỷ lệ đạt gồm cả hỏi lại và từ chối không phải độ chính xác pháp luật.

## Vận hành và giới hạn

Deployment sử dụng Cloudflare Pages, Render và Supabase trên cấu hình Free hiện có. Cold start, hạn mức provider và yêu cầu tương tác Turnstile có thể ảnh hưởng trải nghiệm. Chưa có cam kết SLA; corpus còn coverage gaps và verifier có thể bỏ sót hoặc từ chối quá mức.

Xem [runbook vận hành](docs/OPERATIONS.md) để cấu hình ingress, quản lý quota, rà soát nguồn, triển khai và khôi phục. Trạng thái kiểm chứng deployment nằm trong [artifact triển khai](reports/deployment-ring4.json), tách biệt với đánh giá chất lượng câu trả lời.
