# Bằng chứng triển khai

Cập nhật 13/10/2026 18:10 giờ Việt Nam. Đợt tăng tốc bắt đầu 12/10/2026 16:44:23 UTC; hạn ưu tiên 13/10/2026 07:44:23 UTC đã qua. Kế hoạch M0–M6 chưa hoàn tất. Corpus vẫn staging, con trỏ active release chưa được đặt. Demo chỉ công bố khi toàn bộ 20 ca ở hai chế độ được đối chiếu nguồn và vượt gate; tiêu chí nghiệm thu 80 câu giữ nguyên.

Embedding đã hoàn tất: artifact Colab có 7.610 vector E5 ONNX Q8 384 chiều cho 69 tài liệu, gồm 54 văn bản pháp lý và năm nguồn chính thức cho mỗi dự án. Release `corpus-de584c31fc95f9a2` được staging trên Supabase. Tất cả ID/checksum/contract đã đối chiếu; ba mẫu runtime khớp Colab tuyệt đối. Corpus và checkpoint đã archive private, tải lại đối chiếu byte và khôi phục thành công. Không dùng index trộn model hoặc thiếu vector.

Nguồn QĐ56/2024 đã có toàn văn chính thức để tra cứu lịch sử. Quan hệ thay thế bởi QĐ40/2026 từ 02/04/2026 và quan hệ sửa đổi từng phần được lưu cùng chứng cứ. Corpus source audit đạt; 120 câu và 93 đoạn tham chiếu khớp bộ nghiệm thu khóa checksum. Nguồn chưa đạt và quan hệ thiếu đầu mút được giữ trong báo cáo độ bao phủ, không dùng để kết luận quyền lợi. Tin dự án chỉ cung cấp bối cảnh.

| Mốc | Trạng thái | Bằng chứng / việc còn thiếu |
|---|---|---|
| M0 | Hạ tầng và lượt gọi thật đạt | Pages, Render Free, Supabase chạy thật; Gemini, Workers AI và Groq từng gọi thành công. Groq Free hiện gọi được local/CI/Render. Cần deploy đúng commit cuối sau CI. |
| M1 | Embedding và dữ liệu staging đạt; chưa công bố | 69 tài liệu/54 legal/15 nguồn dự án, đủ 7.610 vector. Audit, archive, parity và restore đạt. Còn gate pháp lý, phát hành có backup và đối chiếu danh mục tại ngày phát hành. |
| M2 | Baseline chạy thật trên staging | Hybrid FTS/pgvector/RRF, hội thoại và dẫn nguồn có sẵn. Đã sửa SQL truy xuất đoạn con; kiểm tra Supabase thật trả tám đoạn không phải đoạn cha. Còn 20 smoke paired đạt và QA URL corpus công bố. |
| M3 | Graph thật; đang kiểm tra chất lượng | Công cụ đọc, hiệu lực cấp điều khoản, chuyển tiếp, verifier source spans, SSE chỉ phát sau kiểm tra. Đã sửa suy luận quá mức từ mốc hiệu lực sang toàn bộ quyền lợi hồ sơ cũ. Còn bộ smoke và benchmark thật trên cấu hình cuối. |
| M4 | Giao diện đã triển khai, kiểm thử kỹ thuật đạt | Hai Vitest, sáu Playwright desktop/mobile và build đạt ở CI. Còn QA hỏi đáp, nguồn, trace trên URL sau khi corpus công bố. |
| M5 | Kỹ thuật nhiều phần đạt; chưa nghiệm thu pháp lý | 121 pytest đạt; CI trước đó đạt; E5 Docker peak RSS 353,73 MiB dưới hard limit 512 MiB. Restore PostgreSQL tách biệt, session isolation, rollback/withdrawal và restart đã đạt. Còn CI image commit cuối, chấm smoke/full benchmark, p95 API sau công bố. |
| M6 | Chưa hoàn tất | Repo, Docker, migration, CI/CD, pipeline và tài liệu đã có. Còn corpus công bố, URL hỏi đáp hợp lệ và báo cáo nghiệm thu đầy đủ. |

Website: https://hanoi-land-law.pages.dev. API: https://land-law-chatbot.onrender.com. Hạ tầng live chưa đồng nghĩa chất lượng pháp lý đã nghiệm thu. `/readyz` hiện báo chưa sẵn sàng vì chưa công bố corpus; chatbot không trả lời nguồn staging như dữ liệu đã phát hành.

CPU embedding chạy trong backend bằng model ONNX Q8 và tokenizer nhẹ; Docker tải model khóa SHA-256 lúc build. Database khoảng 250,72 MiB, archive riêng và checkpoint mới vẫn trong khoảng dự phòng miễn phí. Hai corpus E5/BGE được giữ để đối chiếu; release BGE trước cũng chưa công bố.

Không còn trần LLM/embedding theo ngày do ứng dụng đặt. Giữ sáu lần gọi LLM, 12 công cụ, hai vòng retrieval và 90 giây mỗi lượt, cùng bảo vệ phiên/IP cho website. Không bật billing hoặc nâng gói. Evaluation dùng checkpoint, lưu mọi attempt và chờ theo thông tin token bucket provider giữa lượt; thời gian chờ này được báo riêng, không tính như thời gian xử lý API. Gemini/Workers AI từng chạm quota thực tế; Groq Free là fallback đã được chủ dự án cho phép.

Sự cố unit-test kế thừa DB thật đã được xử lý: dừng workflow, backup mã hóa, gỡ các fixture thử nghiệm và đưa active pointer về chưa công bố. Hai corpus thật đối chiếu không thay đổi. Fixture và workflow được tách môi trường; evaluator chỉ dùng role runtime. Xem `reports/test-environment-recovery.json`.

Bằng chứng: `reports/source-audit.json`, `e5-runtime-parity.json`, `e5-archive-restore.json`, `e5-clean-backup.json`, `postgres-restore.json`, `docker-memory.json`, `cold-start.json`, `infrastructure-smoke.json`, `runtime-tests.json`, `ci.json` và các checkpoint trong `reports/runs`. Kiểm tra release/model/configuration fingerprint và thời điểm từng báo cáo. Báo cáo cấu hình cũ không chứng nhận cấu hình mới.

`data/evaluation/acceptance-freeze.json` giữ 80 câu nghiệm thu; không đổi gold hay ngưỡng để nâng điểm. `reports/retrieval-before-parent-fix.json` lưu chẩn đoán baseline trước sửa đoạn cha, có Recall@8 thấp; đây không phải chứng nhận agentic hoặc đáp án. Chẩn đoán và benchmark mới ghi riêng, không ghép số liệu khác cấu hình. Chưa có bằng chứng đủ Recall@8≥85%, rubric≥85%, claim support≥95% hoặc p95≤60s trên toàn bộ nghiệm thu. Bộ tham chiếu do quá trình triển khai rà soát, không phải thẩm định pháp lý độc lập.
