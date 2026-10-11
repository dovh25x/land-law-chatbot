# Bằng chứng triển khai

Cập nhật ngày 12/10/2026 (giờ Hà Nội). Không đánh dấu toàn bộ kế hoạch hoàn tất khi chưa có URL chạy xuyên suốt và nghiệm thu thật.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Đang kiểm chứng | Repo cấu trúc đã tạo; Supabase migration 001/002 đã chạy; Gemini structured generation thật và embedding 768 thật thành công. Đang triển khai hosting Free và kiểm tra runtime role. |
| M1 | Chưa hoàn tất | 56 nguồn thật, 31 legal verified, mỗi dự án 5 verified; raw/checksum/metadata/quan hệ đã có. Ingestion/embedding staging đang chạy. Toàn văn lịch sử QĐ56/2024 còn thiếu và chặn publish. |
| M2 | Đang kiểm chứng | Hybrid FTS/vector/RRF, baseline, API SSE và hội thoại đã có. Cần kết quả gọi thật với corpus hoàn chỉnh. |
| M3 | Đang kiểm chứng | LangGraph thực, công cụ đọc, retry hữu hạn, verifier, temporal/partial-relation safeguards và unit tests. Cần benchmark thật trên staging. |
| M4 | Đang kiểm chứng | React responsive, chat/filter/source/project/trace/report đã build. Đang QA browser desktop/mobile; không có dữ liệu demo giả. |
| M5 | Chưa hoàn tất | CI, quota/cách ly phiên, RLS, private Storage, backup/restore/rollback, source staging/checksum và bảo vệ secret đã triển khai. Cần kiểm thử tích hợp PostgreSQL, restore rehearsal, đánh giá 80 câu cố định và p95. |
| M6 | Chưa hoàn tất | Docker/Render/Cloudflare workflows và hướng dẫn đã có. Chưa chứng nhận URL/benchmark cuối. |

## Kiểm tra đã thực hiện

- Backend: 22 tests pass ở lần kiểm tra trước khi bổ sung batch/cache/backup. Có thêm tests để kiểm tra các thay đổi mới; chỉ kết quả mới nhất sau chạy lại được coi là bằng chứng cuối.
- Frontend: TypeScript/Vite build, hai SSE protocol tests pass; npm audit zero vulnerabilities sau nâng Vitest. Playwright đã thêm và đang hoàn thiện môi trường Chromium.
- Live API: `gemini-2.5-flash` generation 404, `gemini-3.8-flash` thử đơn giản 503, `gemini-3.5-flash-lite` generation thường/JSON schema 200. `gemini-embedding-2` single và batch hai đoạn đều trả 768 chiều, các vector độc lập.
- Supabase owner connection SELECT 1 pass; migration tạo schema mới và RLS pass. Frontend không có key database/Gemini. Credential scans được chạy; raw secrets không đưa vào báo cáo.
- GitHub repository người dùng cung cấp: tồn tại, trống, token có quyền push. Cloudflare Pages token đọc project được; Render token đọc workspace/services được. Không sửa các ứng dụng khác trong tài khoản.

## Blocker pháp lý

Cổng Hà Nội hiện trỏ tới QĐ56/2024 PDF bản dự thảo với số/ngày trống. VBPL legacy trả shell tải dữ liệu; các đường signed/mirror thử thêm không cung cấp bản lịch sử đủ điều kiện. Mốc hết hiệu lực 02/04/2026 đã được xác minh từ Điều 2 QĐ40/2026, nhưng điều đó không cung cấp nội dung quy định lịch sử. Pipeline bắt buộc giữ QĐ56 trong corpus trước phát hành; không dùng draft hoặc snippet thay toàn văn.

Các source OCR pending và thiếu văn bản đặc thù được ghi cụ thể tại [SOURCES.md](SOURCES.md). Benchmark reference đang ở trạng thái draft; chưa coi đó là nguồn gold đã kiểm chứng, chưa có bằng chứng đạt 85%/95% hoặc p95≤60 giây. Báo cáo kết quả pending/null là chủ đích để tránh chứng nhận sai.
