# Hanoi Land Law Assistant

Nguyên mẫu học thuật học phần **CSE703014 — Đồ án liên ngành**: chatbot tiếng Việt tra cứu pháp luật đất đai Hà Nội bằng Agentic RAG, có nguồn dẫn và trace. **Chưa được thẩm định pháp lý độc lập.**

Website: https://hanoi-land-law.pages.dev · API: https://land-law-chatbot.onrender.com

## Phạm vi
Bồi thường, hỗ trợ, tái định cư và ví dụ dự án Vành đai 4. Thư viện giữ 69 tài liệu/7.610 vector; tài liệu Sông Hồng và Olympic chỉ để tham khảo, không thuộc phạm vi hỏi đáp dự án. Không tiếp nhận hồ sơ cá nhân, tính tiền hoặc xác định thửa đất bằng GIS. Dữ liệu là snapshot, không cập nhật tự động.

## Công nghệ và chức năng
React/TypeScript/Vite; FastAPI/LangGraph; Groq GPT-OSS 120B; E5 ONNX Q8 384 chiều; PostgreSQL/pgvector cloud hoặc SQLite local. Chat hỗ trợ hỏi tiếp, nguồn mở được, trace công cụ và ngày xem xét. Chỉ có Agentic RAG; không có kết quả so sánh đầy đủ để giữ baseline. Không đổi provider/model tự động. Hosting miễn phí có thể ngủ hoặc hết quota.

## Chạy local
Python 3.12+ và Node 24. Cần internet để tải model và gọi Groq; không cần Supabase nếu dùng SQLite.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install --no-deps -e .
cp .env.example .env
# Điền GROQ_API_KEY; giữ DATABASE_URL và ADMIN_DATABASE_URL trống cho local.
.venv/bin/python backend/landlaw/local_embedding.py download models/e5
# Corpus công khai trong gói bàn giao dist/hanoi-land-law-mvp.zip:
.venv/bin/land-law restore data/demo/corpus-backup.json
.venv/bin/uvicorn landlaw.api:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal khác:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Mở http://127.0.0.1:5173. Clone repo không tự có corpus: dùng backup công khai trong gói bàn giao hoặc chuẩn bị snapshot theo tài liệu kỹ thuật. Không restore vào database cloud đang chạy. Không đưa secret vào biến `VITE_*`.

## Kiểm thử và đánh giá

Bản Groq 120B ngày 15/10/2026: **18/20 đạt, 1 một phần, 1 chưa đạt**. S06 lẫn nhóm đối tượng với điều kiện; S08 còn thiếu giải thích điều kiện riêng. Đây là rà soát kỹ thuật có hỗ trợ AI theo nguồn/rubric, chưa được thẩm định pháp lý độc lập. Backend 161 tests, frontend 2 unit tests và 22 E2E đã đạt.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm run test:e2e
```

Bộ 20 câu được khóa bằng checksum trước khi chạy, kết quả phải được rà soát theo câu trả lời thực tế. [Kết quả hiện hành](reports/submission/results.md) chỉ có giá trị trên corpus/model/fingerprint ghi trong artifact; không phải chứng nhận pháp lý. Không sử dụng số liệu phiên bản cũ để mô tả bản mới.

## Tài liệu
- [PRD](docs/PRD.md): yêu cầu và chuẩn đầu ra học phần.
- [Thiết kế kỹ thuật](docs/ARCHITECTURE.md): dữ liệu, retrieval, agent và API.
- [Vận hành](docs/OPERATIONS.md): local, deploy, đánh giá, backup.
- [Rà soát repo](docs/CLEANUP.md): thành phần giữ/xóa.
- [Đóng góp](docs/CONTRIBUTIONS.md): chỉ ghi đóng góp thực tế.

Không tạo báo cáo học phần, slide, kịch bản hoặc video. Sinh viên tự thực hiện phần trình bày bằng lời nói theo yêu cầu giảng viên.
