# Bằng chứng triển khai

Đợt tăng tốc bắt đầu 12/10/2026 16:44:23 UTC, hạn ưu tiên 13/10/2026 07:44:23 UTC. Kế hoạch M0–M6 chưa hoàn tất. Demo chỉ công bố sau gate riêng; toàn bộ tiêu chí nghiệm thu gốc giữ nguyên.

Snapshot 12/10/2026 22:23 UTC: corpus mới `corpus-c30fb243d71ebd2d` có 67 tài liệu, 52 văn bản pháp lý đã đối chiếu, năm nguồn chính thức mỗi dự án; 4,555/7,566 vector BGE-M3 1.024 chiều, còn 3,011 vector. Source audit đạt về provenance/checksum/parse/PDF mapping; điều này không thay thế thẩm định pháp lý. Đã bổ sung các sửa đổi Luật Đất đai, Luật Quy hoạch112/2025 và NĐ155/2026 sửa thủ tục khiếu nại. Giữ các khoảng trống sửa đổi lịch sử chưa xác minh. PDF theo trang và parser phân biệt biểu mẫu đã kiểm thử.

Supabase đã giữ corpus BGE trước `corpus-a6af9cf431b26f71` (47 tài liệu/5.149 vector) chưa công bố. Staging cũ `corpus-217042b8f95fb72f` được dọn sau backup mã hóa có hội thoại; kiểm tra thật sau đó đạt quyền runtime/cách ly phiên và database 158,47 MiB. Storage private: 136 object nguồn đã kiểm tra, dự kiến 479.706.305 byte; còn dự phòng. Seed 8.074 checkpoint trước đó đã restore kiểm tra thành công; checkpoint mới cần archive lại sau embedding.

Gemini 3.5 Flash Lite từng trả lời probe thật nhanh, nhưng các lượt tiếp theo báo daily quota với RetryInfo đến khoảng 00:00 UTC. Gemini 2.5 Flash/Flash Lite trả HTTP404 cho tài khoản khi probe; không suy model miễn phí trong bảng giá là endpoint tài khoản gọi được. Qwen miễn phí đã được chủ dự án cho phép và adapter đã gọi thật, nhưng Workers AI cũng báo hết daily allocation. Không retry liên tục khi provider yêu cầu chờ. Giữ checkpoint và tiếp tục các việc độc lập. Không có trần LLM/embedding theo ngày do ứng dụng đặt; giữ 6 LLM/12 tool/2 retrieval/90 giây và bảo vệ public. Không bật billing hoặc nâng gói.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Hạ tầng và lượt gọi thật đã đạt | Pages và Render Free live; Supabase role riêng, Gemini/Workers AI gọi thật. CI commit 1d1cf8ba đạt; bản sửa mới cần CI/deploy riêng. |
| M1 | Corpus mở rộng đang staging | 67 tài liệu/52 legal/5 nguồn mỗi dự án. Còn 3,011 vector và kiểm chứng indexing trên DB; không công bố index thiếu vector. Nguồn pending/quan hệ thiếu đầu mút được khai báo. |
| M2 | Luồng baseline thật trên staging | Hybrid FTS/pgvector/RRF, hội thoại, dẫn nguồn và SSE đã có. Còn smoke pháp lý đạt trên cấu hình cuối và kiểm chứng URL. |
| M3 | Graph thật, đang xác minh chất lượng | Công cụ đọc, hiệu lực cấp điều khoản, sửa đổi có phạm vi, verifier bằng source spans và retry hữu hạn. Đã sửa đếm công cụ liên quan, lỗi nhầm ngày ban hành/hiệu lực và hỏi lại quá mức cho câu chung; cần chạy lại provider thật sau quota. |
| M4 | Giao diện có URL và kiểm thử | 2 Vitest, build và 6 Playwright desktop/mobile đạt trên bản sửa modal nguồn. URL hiện corpus chưa công bố; còn QA hỏi đáp công khai sau phát hành. |
| M5 | Kỹ thuật nhiều phần đạt, chưa nghiệm thu | 100 pytest đạt; Postgres isolation/permissions/reserve đạt. Backup và restore PostgreSQL độc lập đã đạt cho corpus trước. 120 rubric đã đối chiếu nguồn/hành vi, 93 đoạn tham chiếu, 80 acceptance đã khóa checksum. Còn đánh giá câu trả lời thật, recovery release mới, p95/cold start/restart sau công bố. |
| M6 | Chưa hoàn tất | Repo, Docker, migration, CI/CD, pipeline, tài liệu vận hành và kịch bản demo có sẵn. Còn gate demo, URL hỏi đáp corpus mới và báo cáo nghiệm thu đầy đủ. |

Website: https://hanoi-land-law.pages.dev. API: https://land-law-chatbot.onrender.com. Hạ tầng live chưa đồng nghĩa corpus đã công bố hoặc chất lượng đã nghiệm thu.

Bằng chứng tại `reports/corpus-coverage.json`, `source-audit.json`, `source-discovery.json`, `runtime-tests.json`, `postgres-integration.json`, `storage-archive.json`, `embedding-seed.json`, `checkpoint-restore.json` và `postgres-restore.json`. Kiểm tra release/model/configuration fingerprint và thời điểm từng báo cáo; artifact cũ không xác nhận cấu hình mới.

`data/evaluation/acceptance-freeze.json` giữ 80 câu nghiệm thu; validator từ chối checksum/gold không khớp corpus trước chạy acceptance. Rubric nguồn được AI engineer rà soát, không phải thẩm định pháp lý độc lập và không phải điểm đạt câu trả lời. Chưa có bằng chứng Recall@8≥85%, rubric≥85%, claim support≥95% hoặc p95≤60s trên toàn bộ nghiệm thu. Các run quota/lỗi vẫn được giữ; không đổi gold/ngưỡng để nâng điểm.
