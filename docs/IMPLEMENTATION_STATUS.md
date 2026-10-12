# Bằng chứng triển khai

Đợt tăng tốc bắt đầu 12/10/2026 16:44:23 UTC, hạn ưu tiên 13/10/2026 07:44:23 UTC. Kế hoạch M0–M6 chưa hoàn tất. Demo chỉ công bố sau gate riêng; toàn bộ tiêu chí nghiệm thu gốc giữ nguyên.

Snapshot tiến độ 12/10/2026: release staging `corpus-a6af9cf431b26f71` có 47 tài liệu, 32 văn bản pháp lý đã kiểm tra, năm nguồn chính thức mỗi dự án và đủ 5.149 vector BGE-M3 1.024 chiều. QĐ56/2024 lịch sử đã lấy từ toàn văn snapshot chính thức VBPL, lưu cả nguồn gốc và cách chuẩn hóa; giới hạn tuổi cache được ghi rõ trong SOURCES. Source audit đạt. Sau backup mã hóa và dọn bốn staging cũ, PostgreSQL khoảng 273 MB; giữ release BGE đầy đủ trước đó và release mới. Storage private khoảng 362 MB sau seed mới. 8.074 checkpoint giữ được, có shard/manifest/checksum để phục hồi.

Gemini nhanh trả quota theo ngày; model Gemini còn khả dụng có độ trễ gây timeout. Chủ dự án đã cho phép Qwen miễn phí qua Workers AI làm dự phòng. Adapter có JSON schema, kiểm tra Pydantic, cùng verifier và không hiển thị reasoning. Hai chế độ dùng cùng Qwen/BGE/corpus khi chạy smoke. Các run trước đó chưa đạt và không được dùng để công bố. Không có trần LLM/embedding theo ngày do ứng dụng đặt; giới hạn mỗi lượt và chống lạm dụng public vẫn giữ. Không bật billing hoặc nâng gói.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Hạ tầng và lượt gọi thật đã đạt | Pages và Render Free live; Supabase role riêng, Gemini/Workers AI gọi thật. CI trước đợt sửa mới đạt; chờ CI/deploy cấu hình Qwen mới. |
| M1 | Corpus đầy đủ vector đang staging | 47 tài liệu/32 legal/5 nguồn mỗi dự án; source audit đạt. QĐ56 đã bổ sung. Nguồn OCR/chưa duyệt và quan hệ thiếu đầu mút tiếp tục cách ly, khai báo coverage_gaps. Chưa công bố release. |
| M2 | Luồng baseline thật trên staging | Hybrid FTS/pgvector/RRF, hội thoại, dẫn nguồn và SSE đã có. Chờ smoke pháp lý đạt trên cấu hình cuối và kiểm chứng URL. |
| M3 | Luồng graph thật trên staging | Công cụ đọc, hiệu lực cấp điều khoản, quan hệ sửa đổi, verifier có quote, retry hữu hạn. Đang sửa lỗi phát hiện bằng lượt provider thật; chưa đạt gate 20 ca. |
| M4 | Giao diện đã QA và có URL | Desktop/mobile và SSE protocol đã qua kiểm thử. URL hiện hiển thị corpus chưa công bố; cần QA hỏi đáp sau phát hành. |
| M5 | Nhiều kiểm tra đạt, chưa nghiệm thu | Suite backend mới, PostgreSQL permissions/session isolation/atomic quota đạt; backup mã hóa, restore PostgreSQL độc lập đã có bằng chứng thật cho corpus trước. Còn recovery với release mới, full benchmark, p95, cold start/restart sau công bố. |
| M6 | Chưa hoàn tất | Repo, Docker, migration, CI/CD, pipeline, vận hành và demo có sẵn. Còn gate, deploy cuối, URL hỏi đáp corpus mới và báo cáo nghiệm thu. |

Website: https://hanoi-land-law.pages.dev. API: https://land-law-chatbot.onrender.com. Chúng đang live về hạ tầng; chưa đồng nghĩa corpus đã công bố hoặc nghiệm thu pháp lý.

Bằng chứng được lưu trong `reports/corpus-coverage.json`, `source-audit.json`, `source-discovery.json`, `runtime-tests.json`, `postgres-integration.json`, `storage-archive.json`, `embedding-seed.json`, `checkpoint-restore.json` và `postgres-restore.json`. Báo cáo benchmark/smoke có release/model/configuration fingerprint; phải kiểm tra khớp release và cấu hình đang hoạt động. Các artifact của commit/corpus cũ không xác nhận cấu hình mới.

Bộ 120 câu vẫn cần rà soát gold/rubric theo nguồn và đóng băng 80 câu nghiệm thu trước chạy cuối. Không có bằng chứng đạt Recall@8≥85%, rubric≥85%, claim support≥95% và p95≤60s trên toàn bộ nghiệm thu. Không gán đạt dựa trên giao diện hay vài câu trả lời.
