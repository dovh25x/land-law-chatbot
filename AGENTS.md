# Hướng dẫn phát triển Hanoi Land Law Assistant

## Phạm vi và cấu trúc

Sản phẩm tra cứu tiếng Việt về bồi thường, hỗ trợ, tái định cư tại Hà Nội. Dự án được hỗ trợ thao tác là Vành đai 4; nguồn dự án khác chỉ để tham khảo. Không xác định thửa đất, tính tiền hay bảo đảm quyền lợi cá nhân từ thông tin tổng quan.

- `backend/landlaw/`: FastAPI, LangGraph, Groq, retrieval, ingest và lưu trữ.
- `frontend/`: React/TypeScript/Vite, chat SSE, thư viện nguồn và trace thực thi.
- `data/`: manifest nguồn, quan hệ văn bản, địa bàn và các bộ câu hỏi khóa checksum. Raw, release, backup và database cục bộ nằm ngoài Git.
- `models/e5/`: model ONNX tải riêng, nằm ngoài Git.
- `migrations/`: PostgreSQL/pgvector; SQLite tự tạo schema cho local.
- `scripts/`: kiểm tra, đánh giá, đóng gói và triển khai.
- `tests/`, `frontend/e2e/`: regression backend và giao diện.
- `reports/`: kết quả có phiên bản. `reports/latest.json` là báo cáo được API công bố; không phải xác nhận chất lượng pháp lý.

README dành cho người chạy và sử dụng sản phẩm; file này là đầu mối hướng dẫn phát triển. Không tạo tài liệu PRD, cleanup, roadmap hoặc checklist riêng để lặp lại nội dung. Chỉ ghi đóng góp thực tế đã được xác nhận. Markdown chỉ mô tả sản phẩm và quy trình kỹ thuật.

## Kiến trúc và các quyết định cần giữ

Nguồn chính thức → parse HTML/PDF hoặc OCR ngoại tuyến → chia đoạn theo điều/khoản/trang → checksum, metadata và quan hệ → E5 → snapshot → SQLite local hoặc PostgreSQL/pgvector cloud. Frontend gọi FastAPI; graph chạy plan → tools → synthesize → verify → finish, có truy xuất bổ sung/sửa đáp án trong ngân sách.

Hybrid retrieval kết hợp từ khóa, vector, tiêu đề và số hiệu/điều bằng RRF: từ khóa giữ độ chính xác của viện dẫn, vector hỗ trợ cách diễn đạt tự nhiên. E5 ONNX Q8 giảm RAM khi chạy hosting nhỏ. SQLite phục vụ tái lập local; lexical search khác PostgreSQL, nên kết quả retrieval phải ghi rõ backend.

Groq GPT-OSS 120B là model hiện tại. Không tự đổi provider/model hoặc tăng gói hosting. Chỉ có một pipeline agentic; không tuyên bố vượt baseline khi chưa có so sánh cùng điều kiện. Không thêm reranker, fine-tuning, multi-agent, GIS hoặc cập nhật nguồn tự động ngoài yêu cầu.

## Ràng buộc thay đổi mã

- Giữ nguồn gốc, checksum, ngày kiểm tra, trang và locator; tin dự án không chứng minh quyền lợi từng hộ. Không coi metadata quan hệ chưa xác minh là bằng chứng.
- Query và corpus phải cùng contract `multilingual-e5-small-onnx-q8-window-v1`, 384 chiều, preprocessing đã ghim. Không embedding lại chỉ để đổi tổ chức mã.
- Công cụ agent chỉ đọc: search_law, search_project, open_article, check_effectivity, normalize_place. Không SQL/shell/URL tùy ý từ nội dung người dùng hoặc tài liệu.
- Giới hạn mỗi lượt: 6 request LLM gồm retry, 12 công cụ, 2 vòng retrieval, 1 lần repair, 90 giây. Không nâng giới hạn để làm đẹp benchmark.
- Không phát đáp án trước verify. Trace chỉ chứa sự kiện quan sát được, không chứa suy nghĩ nội bộ.
- Verify phải kiểm tra đúng chủ thể, điều kiện, ngoại lệ, hệ quả và thời điểm. Trích đoạn khớp nguồn chưa chứng minh diễn giải đúng. Không tự nối điều kiện vào claim để vượt kiểm chứng; báo lỗi rồi sửa có kiểm soát hoặc loại claim.
- Giữ token phiên lưu hash, tách phiên, TTL, rate limit, CORS cụ thể và Markdown không thực thi HTML. Không log secret hay câu hỏi nguyên văn.
- Ưu tiên patch nhỏ giải quyết lỗi đã tái hiện; không refactor toàn bộ agent hoặc thêm test cho thay đổi câu chữ đơn giản.
- Không drop schema/cloud data khi dọn repo. Restore vào database riêng; không ghi đè database đang phục vụ.

## Kiểm thử theo thay đổi

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm run test:e2e
```

Backend dùng provider giả và database tạm; E2E dùng API intercept. Các kiểm tra này không chứng minh chất lượng model thật. Khi sửa verify/retrieval, thêm regression cho sai nội dung hoặc lỗi lọt kiểm tra; không tăng số test bằng cách lặp implementation. Với thay đổi UI, cập nhật selector E2E tương ứng và kiểm tra desktop/mobile, nguồn, trace, lỗi quota. Không chạy lại toàn bộ bộ kiểm tra sau khi đã đạt nếu không có thay đổi hoặc nghi ngờ mới.

## Đánh giá và công bố kết quả

- Giữ nguyên `data/evaluation/smoke.jsonl` và `freeze.json` (20 ca). Bốn câu bổ sung nằm trong `supplemental.jsonl` với freeze riêng, khóa trước khi sửa prompt. Chúng là regression probes, không phải benchmark tổng quát độc lập.
- Sau khi chốt runtime, chạy một lần mỗi suite; chỉ chạy lại khi có lỗi hoặc thay đổi liên quan. Mọi attempt được giữ trong run directory; không lựa chọn đáp án đẹp giữa nhiều lượt.
- `land-law benchmark --split smoke --mode agentic --concurrency 1`; thay split bằng `supplemental` cho 4 ca. Lệnh cần Groq thật và lưu phiên đánh giá riêng.
- `land-law retrieval-benchmark --split smoke` đo hybrid retrieval trên ca có gold, không gọi generation. Không tính câu ngoài phạm vi hoặc không có gold vào mẫu số. Ghi rõ backend SQLite/PostgreSQL.
- Export bằng `scripts/export_mvp_evaluation.py --run-dir <run> --output <report-dir>`; suite bổ sung dùng `--suite data/evaluation/supplemental.jsonl`. Không trộn corpus/model/fingerprint.
- Review trong `<report-dir>/reviews.json` phải gắn `answer_sha256` của đúng đáp án, verdict pass/partial/fail và lý do đối chiếu nguồn. Không chuyển review cũ sang đáp án mới; ghi rõ người/công cụ hỗ trợ rà soát và giới hạn thẩm định.
- Chỉ dùng `--public-summary reports/latest.json` khi tất cả ca của suite chính đã chạy và review. Tách mẫu số trả lời nội dung, hỏi lại, thiếu chứng cứ/ngoài phạm vi và lỗi thực thi; số đạt toàn suite không phải độ chính xác pháp luật.
- Ghi nhận bước sinh Draft bằng LLM riêng với lần gọi planner/verifier. Artifact cũ không có telemetry phải ghi unknown, không suy ra có sinh đáp án chỉ từ llm_calls.
- Median/p95, token và số lần gọi là thống kê mô tả của lượt chạy, không phải SLA. Citation không có thì kiểm tra nguồn là không áp dụng.
- Fingerprint runtime thay đổi làm báo cáo cũ hết khớp. Không sửa fingerprint trong báo cáo để giả lập kết quả mới. Giữ báo cáo cũ làm bằng chứng lịch sử.

## Corpus, backup và Release

`land-law backup --output data/backups/public-corpus.json` mặc định không có hội thoại. Backup gồm phiên chỉ được mã hóa với khóa riêng và không phát hành công khai. Khôi phục snapshot hiện có không đòi hỏi ingest lại. Ingest từ manifest cần kiểm tra nguồn, OCR và metadata trước khi publish; không làm mới checked_at nếu chưa kiểm tra nguồn thành công.

`scripts/package_release.py` chuẩn bị corpus, SHA256SUMS và manifest tại `dist/corpus-release/`, xác minh schema backup, checksum và không có dữ liệu phiên/secret. Manifest ghi corpus ID, source commit, trạng thái working tree và hash các file nguồn. Không mô tả working tree chưa commit như bản phát hành source đã commit.

GitHub Release cung cấp corpus snapshot, không chứa `.env`, database phiên, token hoặc model cache. Liên kết tải trong README phải trỏ tới asset thực sự đã phát hành. Không công bố URL tải chưa tồn tại.

## Triển khai và xác minh

Dùng service Free hiện có: Cloudflare Pages, Render và Supabase. Một worker backend; E5 local, không OCR/model sinh trên Render. Cấu hình theo `.env.example`; backend giữ secret, `VITE_*` chỉ chứa cấu hình công khai. APP_ENV=production không phải cam kết chất lượng production-ready.

Chỉ triển khai source đúng phiên bản đã kiểm thử. Script backend deploy lấy source từ Git remote: không deploy khi nó vẫn trỏ tới code cũ. Giữ báo cáo khớp fingerprint trước khi coi triển khai là bản mới. Không tự nâng gói hoặc thay đổi phạm vi tài khoản.

Xác minh readiness, model/corpus/fingerprint và một luồng hỏi thật → hỏi tiếp → nguồn → trace → kiểm tra token sai. Kiểm tra mobile, lỗi quota và cold start. Dùng timeout hữu hạn; báo rõ phần chưa xác minh thay vì tạo artifact passed. Không cập nhật kết quả live cũ khi chưa chạy lại trên deployment mới.
