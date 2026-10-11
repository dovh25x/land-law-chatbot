# Bằng chứng triển khai

Cập nhật ngày 12/10/2026 (giờ Hà Nội). Kế hoạch M0–M6 chưa hoàn tất; không công bố corpus hoặc chứng nhận chất lượng khi chưa qua gate.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Hạ tầng và lượt gọi thật đã đạt | GitHub CI Python 3.12/frontend/Docker pass; Cloudflare và Render Docker Free đã live. Smoke URL thực: database, CORS, cách ly phiên, lưu hội thoại và một lần gọi Gemini qua SSE đều pass. Model/embedding/quota đã kiểm tra; memory quan sát khoảng 90 MB / giới hạn 512 MB, chưa là tải corpus đầy đủ. |
| M1 | Chưa hoàn tất | Staging 46 tài liệu: 31 legal verified và 5 nguồn mỗi dự án; 6.546 đoạn, 945 vector thật đã checkpoint. Thiếu toàn văn lịch sử QĐ56/2024 và embedding còn lại; publication_ready=false. 60 objects nguồn/manifest đã lưu Storage private, khoảng 50 MB. |
| M2 | Đã có luồng thật trên staging | PostgreSQL FTS/pgvector/RRF, baseline, SSE và hội thoại đã triển khai. Có development benchmark gọi Gemini thật; chưa đủ corpus/80 câu nghiệm thu. |
| M3 | Đã có luồng thật trên staging | LangGraph, công cụ đọc, hiệu lực cấp điều khoản, partial amendments, hỏi lại, verifier, sửa JSON một lần và ngân sách hữu hạn đã kiểm thử. Có lượt thật truy xuất bổ sung; chưa đạt chứng nhận benchmark. |
| M4 | Giao diện đã QA và có URL | https://hanoi-land-law.pages.dev đã nối API https://land-law-chatbot.onrender.com, hiển thị corpus đang chờ công bố. 6 browser checks pass desktop/mobile, 2 SSE protocol tests pass; kiểm tra trình duyệt mobile trên URL thật đã qua. Còn kiểm tra luồng hỏi đáp pháp lý sau khi công bố corpus. |
| M5 | Hoàn thành nhiều kiểm tra, chưa nghiệm thu | 38 backend tests pass; npm audit 0 vulnerabilities. Live PostgreSQL privileges/session isolation/atomic quota/RLS pass, database khoảng 109 MB. Restore/rollback với corpus thật và backup hội thoại mã hóa pass trên database thử nghiệm tách biệt. Còn benchmark cố định, cold start và fault smoke trên URL. |
| M6 | Chưa hoàn tất | Mã nguồn, Docker, migration, workflow, benchmark, pipeline, tài liệu vận hành và demo đã có. Frontend/API đã live và smoke hạ tầng pass. Còn công bố corpus đầy đủ và nghiệm thu pháp lý/hiệu năng cuối. |

## Báo cáo kiểm chứng

- [Corpus coverage](../reports/corpus-coverage.json): tất cả nguồn staging có checksum/nguồn truy nguyên; nguồn pending/OCR/draft bị cách ly. Độ bao phủ số lượng đạt, điều kiện phát hành chưa đạt.
- [PostgreSQL integration](../reports/postgres-integration.json): runtime chỉ đọc corpus, anonymous bị từ chối, hai phiên cách ly, bộ đếm atomic và dung lượng dưới 350 MB.
- [Storage archive](../reports/storage-archive.json): bucket private, immutable source objects và giới hạn dự phòng 700 MB.
- [Restore rehearsal](../reports/restore-rehearsal.json): dùng corpus thật trong SQLite tách biệt; giữ checksum, số đoạn, hội thoại, trace, token hash, rollback và forward restore. Không đổi pointer PostgreSQL công khai.
- [Frontend deployment](../reports/frontend-deployment.json): URL HTTP 200/CSP, mobile kết nối API thật và ba hồ sơ dự án; không đồng nghĩa nghiệm thu pháp lý.
- [Infrastructure smoke](../reports/infrastructure-smoke.json): lượt Gemini thật trên URL, trả thiếu căn cứ đúng khi corpus chưa công bố; không chứng nhận câu trả lời pháp lý.
- [Render memory](../reports/render-memory.json): số liệu API nền tảng trong bài smoke; chưa đo tải với corpus công bố.
- [CI](../reports/ci.json): kiểm thử Python 3.12, frontend, audit và Docker thật trên GitHub.
- [Development benchmark](../reports/latest.json) và [HTML](../reports/benchmark.html): gọi model thật, checkpoint theo corpus/model/dataset/configuration. Số liệu từ vài câu dev không chứng minh tiêu chí 80 câu; recall/nội dung/claim support chưa rà soát là null.

Lượt phát triển đầu tiên phát hiện tải archive vector quá lớn và thời gian trên 90 giây. Đã tách metadata thành migration 003, giảm dữ liệu trong truy vấn và bỏ transaction không cần thiết cho SELECT; kiểm tra exact-article trên PostgreSQL giảm còn khoảng 3 giây. Timeout hiện bao gồm cả tải metadata/lịch sử. Một output JSON sai schema đã dẫn đến bổ sung một lần sửa trong ngân sách; các run cũ giữ trong reports/runs (không commit) để đối chiếu.

## Những việc còn chặn phát hành

1. QĐ56/2024: attachment cổng Hà Nội đang là draft số/ngày trống. VBPL legacy bị chặn hoặc không có toàn văn tải được; không dùng draft hay search snippet làm corpus. Tìm kiếm Công báo ngày 12/10 theo từ khóa `56/2024` trả ba văn bản sửa đổi/đính chính, không có bản gốc. Mốc thay thế xác minh từ QĐ40/2026 không cung cấp nội dung lịch sử. Chi tiết tại [SOURCES](SOURCES.md).
2. Gemini embedding Free đã trả daily quota 429. Checkpoint giữ 945 vector; còn 5.601 đoạn. Tiếp tục khi provider cho phép, tối đa 900 input/ngày mặc định, không nâng phí. Retry-After/RetryInfo được giữ, không retry vòng lặp vô hạn.
3. Bộ 120 câu (40 dev/80 acceptance) có rubric/reference draft. Cần source-check gold và rà soát kết quả thật; chưa có bằng chứng đạt Recall@8≥85%, rubric≥85%, claim support≥95%, critical temporal zero errors hoặc p95≤60s trên nghiệm thu.
4. GitHub token hiện không đọc được Actions Secrets (HTTP 403). Workflow tiếp tục embedding/backup đã chuẩn bị nhưng vẫn cần Secrets quyền ghi hoặc cấu hình qua GitHub UI; job phụ thuộc secret được giữ disabled bằng variables.

Danh sách và bằng chứng được cập nhật sau mỗi lần deploy/đánh giá; không tự coi giao diện hoặc development benchmark là hoàn tất M0–M6.
