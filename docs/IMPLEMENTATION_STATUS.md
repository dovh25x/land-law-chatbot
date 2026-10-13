# Bằng chứng triển khai

Đợt tăng tốc bắt đầu 12/10/2026 16:44:23 UTC, hạn ưu tiên 13/10/2026 07:44:23 UTC. Kế hoạch M0–M6 chưa hoàn tất. Demo chỉ công bố sau gate riêng; toàn bộ tiêu chí nghiệm thu gốc giữ nguyên.

Snapshot 13/10/2026 12:18 giờ Việt Nam: Colab đã xử lý đủ 7.610 vector E5 ONNX Q8 384 chiều (69 tài liệu, 54 văn bản pháp lý, năm nguồn mỗi dự án). Artifact đã đối chiếu toàn bộ ID/checksum/contract và nhập checkpoint. Release `corpus-de584c31fc95f9a2` đã staging, source audit đạt và 120 câu/93 đoạn tham chiếu vẫn khớp bộ nghiệm thu đã khóa. Backend đã bổ sung provider CPU với tokenizer nhẹ, migration/index 384 chiều và Docker tải model khóa SHA-256 lúc build. 117 pytest đạt. Vector runtime đã đối chiếu khớp tuyệt đối với Colab trên ba mẫu; hybrid 384 chiều chạy thật, DB 250,72 MiB và checkpoint 7.603 khóa đã lưu private. Còn kiểm chứng RAM image thực tế, CI/deploy mới, 20 ca smoke ở hai chế độ, recovery release mới và toàn bộ benchmark nghiệm thu. Chưa công bố corpus, chưa đạt toàn kế hoạch.

Supabase đã giữ corpus BGE trước `corpus-a6af9cf431b26f71` (47 tài liệu/5.149 vector) chưa công bố. Staging cũ `corpus-217042b8f95fb72f` được dọn sau backup mã hóa có hội thoại; kiểm tra thật sau đó đạt quyền runtime/cách ly phiên và database 158,47 MiB. Storage private: 136 object nguồn đã kiểm tra, dự kiến 479.706.305 byte; còn dự phòng. Seed 8.074 checkpoint trước đó đã restore kiểm tra thành công; checkpoint mới cần archive lại sau embedding.

Gemini 3.5 Flash Lite từng trả lời probe thật nhanh, nhưng các lượt tiếp theo báo daily quota với RetryInfo đến khoảng 00:00 UTC. Gemini 2.5 Flash/Flash Lite trả HTTP404 cho tài khoản khi probe; không suy model miễn phí trong bảng giá là endpoint tài khoản gọi được. Qwen miễn phí đã được chủ dự án cho phép và adapter đã gọi thật, nhưng Workers AI cũng báo hết daily allocation. Không retry liên tục khi provider yêu cầu chờ. Giữ checkpoint và tiếp tục các việc độc lập. Không có trần LLM/embedding theo ngày do ứng dụng đặt; giữ 6 LLM/12 tool/2 retrieval/90 giây và bảo vệ public. Không bật billing hoặc nâng gói.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Hạ tầng và lượt gọi thật đã đạt | Pages và Render Free live; Supabase role riêng, Gemini/Workers AI gọi thật. CI commit 9a7bfe04 đạt; đúng commit đã deploy Render và Pages. Sửa bổ sung cấp điều khoản cần CI riêng. |
| M1 | Corpus mở rộng đang staging | 69 tài liệu/54 legal/5 nguồn mỗi dự án, đủ 7.610 vector E5. Còn gate pháp lý và kiểm chứng indexing/khôi phục trên DB; không công bố index thiếu vector. Nguồn pending/quan hệ thiếu đầu mút được khai báo. |
| M2 | Luồng baseline thật trên staging | Hybrid FTS/pgvector/RRF, hội thoại, dẫn nguồn và SSE đã có. Còn smoke pháp lý đạt trên cấu hình cuối và kiểm chứng URL. |
| M3 | Graph thật, đang xác minh chất lượng | Công cụ đọc, hiệu lực cấp điều khoản, sửa đổi có phạm vi, verifier bằng source spans và retry hữu hạn. Đã sửa đếm công cụ liên quan, lỗi nhầm ngày ban hành/hiệu lực và hỏi lại quá mức cho câu chung; cần chạy lại provider thật sau quota. |
| M4 | Giao diện có URL và kiểm thử | 2 Vitest, build và 6 Playwright desktop/mobile đạt trên bản sửa modal nguồn. URL hiện corpus chưa công bố; còn QA hỏi đáp công khai sau phát hành. |
| M5 | Kỹ thuật nhiều phần đạt, chưa nghiệm thu | 117 pytest đạt; Postgres isolation/permissions/reserve đạt. Backup và restore PostgreSQL độc lập đã đạt cho corpus trước. 120 rubric đã đối chiếu nguồn/hành vi, 93 đoạn tham chiếu, 80 acceptance đã khóa checksum. Còn đánh giá câu trả lời thật, recovery release mới, p95/cold start/restart sau công bố. |
| M6 | Chưa hoàn tất | Repo, Docker, migration, CI/CD, pipeline, tài liệu vận hành và kịch bản demo có sẵn. Còn gate demo, URL hỏi đáp corpus mới và báo cáo nghiệm thu đầy đủ. |

Website: https://hanoi-land-law.pages.dev. API: https://land-law-chatbot.onrender.com. Hạ tầng live chưa đồng nghĩa corpus đã công bố hoặc chất lượng đã nghiệm thu.

Bằng chứng tại `reports/corpus-coverage.json`, `source-audit.json`, `source-discovery.json`, `runtime-tests.json`, `postgres-integration.json`, `storage-archive.json`, `embedding-seed.json`, `checkpoint-restore.json` và `postgres-restore.json`. Kiểm tra release/model/configuration fingerprint và thời điểm từng báo cáo; artifact cũ không xác nhận cấu hình mới.

`data/evaluation/acceptance-freeze.json` giữ 80 câu nghiệm thu; validator từ chối checksum/gold không khớp corpus trước chạy acceptance. Rubric nguồn được AI engineer rà soát, không phải thẩm định pháp lý độc lập và không phải điểm đạt câu trả lời. Chưa có bằng chứng Recall@8≥85%, rubric≥85%, claim support≥95% hoặc p95≤60s trên toàn bộ nghiệm thu. Các run quota/lỗi vẫn được giữ; không đổi gold/ngưỡng để nâng điểm.

Groq Free đã được chủ dự án cho phép và adapter JSON Schema đã qua kiểm thử. Request từ mạng máy phát triển hiện trả HTTP 403 “Access denied. Please check your network settings.” trên cả danh sách model và probe tối thiểu. Đang kiểm chứng độc lập trên GitHub runner/Render; không kết luận token sai hoặc hết quota từ lỗi này. Workflow evaluation chỉ chạy checkpoint và lưu kết quả, không tự chấm đạt hoặc công bố corpus.

CI commit `45be38c` đạt. Docker E5 thực tế peak RSS 353,73 MiB dưới hard limit 512 MiB. Groq gọi được trên Render và GitHub runner, local bị chặn mạng. Request pháp lý đầu tiên bị HTTP413 do ngữ cảnh vượt free request capacity; đang kiểm thử chọn đoạn nguyên vẹn và loại nội dung lặp. Sự cố unit-test kế thừa DB thật đã dừng và gỡ fixture, hai corpus thật đối chiếu không thay đổi, pointer quay về chưa công bố; workflow evaluator dùng role runtime và test tách môi trường. Xem `reports/test-environment-recovery.json`.
