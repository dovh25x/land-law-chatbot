# Bản MVP học thuật dùng Groq — 15/10/2026

Phạm vi hiện hành là đồ án liên ngành, không còn lấy M0–M6 production làm điều kiện nộp. Bản nộp chọn Groq `openai/gpt-oss-20b`, E5 ONNX Q8 384 chiều, corpus 69 tài liệu / 7.610 vector. Render không chứa NVIDIA_API_KEY. Đủ 20 ca agentic CLI đã thực thi và rà soát: 17 pass, 3 partial, 0 fail; chi tiết tại [kết quả](../reports/submission/results.md). HTTPS/browser và video được ghi riêng, không suy từ CLI.

Bằng chứng mới: `reports/submission/evaluation.json`, `reviews.json`, `mvp-handoff.json`; báo cáo và 10 slide trong `docs/submission/`. Mọi nội dung bên dưới là lịch sử của yêu cầu production và không chứng nhận chất lượng bản Groq. Ba ca S04/S11/S16 còn thiếu ý hoặc diễn đạt giới hạn chưa rõ; không tuyên bố thẩm định pháp lý độc lập.

---

> **Phạm vi hiện hành:** đồ án học thuật theo [SCOPE](submission/SCOPE.md). Các mốc production và tiêu chí bên dưới được giữ như lịch sử, không còn là điều kiện nộp học phần. Không đổi nghĩa trạng thái nghiệm thu cũ.

# Bằng chứng triển khai

Cập nhật NVIDIA 14/10/2026: provider ưu tiên `nvidia`, model `nvidia/nemotron-3-super-120b-a12b`, fingerprint `2d7103d1`. Khóa thật đã xác thực, sáu kết quả core S01/S07/S09 được đối chiếu nguồn, 185 tests và CI `38503262312` đạt; peak Docker 353,75 MiB dưới giới hạn 512 MiB. Render đã triển khai commit `3d24a5a`; cả baseline và agentic trả lời qua HTTPS bằng NVIDIA, trích dẫn Điều104 khớp nguồn, cách ly phiên/trace/lịch sử đạt. Corpus/E5 giữ nguyên. Bằng chứng công bố Groq được giữ bất biến; báo cáo của cấu hình cũ không chứng nhận NVIDIA. Benchmark đầy đủ còn pending. Xem `reports/nvidia-integration.json` và `reports/live-demo.json` để xác nhận tình trạng kiểm tra HTTPS mới nhất.

Các số liệu và hạn chế dưới đây là checkpoint Groq ngày 13/10, được giữ để đối chiếu lịch sử; không phải điểm đánh giá NVIDIA.

Cập nhật 13/10/2026 23:53 giờ Việt Nam. Chủ dự án đã ưu tiên demo kỹ thuật và cho phép hoàn thiện đánh giá pháp lý sau. Chế độ `technical_demo` có gate riêng; không đổi gate `demo` đầy đủ hoặc `accepted`. Corpus đã công bố ở chế độ demo kỹ thuật; `/readyz` HTTP 200 và hai đáp án baseline/agentic qua HTTPS đạt kiểm tra vận hành. Giao diện desktop/mobile, nguồn, trace và lịch sử đã kiểm tra thật, không dùng mocks. Kế hoạch M0–M6 ban đầu chưa nghiệm thu toàn bộ, hạn ưu tiên 15 giờ đã qua.

Embedding hoàn tất: **7.610 vector E5 ONNX Q8, 384 chiều**, cho **69 tài liệu** (54 pháp lý và năm nguồn chính thức mỗi dự án), release `corpus-de584c31fc95f9a2`. Runtime đối chiếu ba mẫu Colab khớp tuyệt đối; archive/checkpoint private và restore đạt. Backend dùng CPU ONNX, không Torch/OCR; không trộn model. Toàn văn QĐ56/2024 lịch sử đã có; QĐ40/2026 thay thế từ 02/04/2026 được chứng minh bằng Điều 2. Coverage tối thiểu và nguồn bắt buộc đạt; năm nguồn bổ sung còn thiếu và bốn quan hệ thiếu đầu mút vẫn công khai, không dùng làm căn cứ quyền lợi.

Cấu hình hiện tại `b059cbbd`: Groq Free `openai/gpt-oss-20b` và E5. Khóa mới được đồng bộ lên Render/GitHub. Sáu kết quả thật S01/S07/S09 ở cả baseline/agentic đã đối chiếu nguồn và đạt; đây là gate demo kỹ thuật, **không phải nghiệm thu 20 cặp smoke hoặc 80 câu**. Chỉ số chất lượng tổng hợp vẫn withheld/null. Bộ 120 câu/93 đoạn tham chiếu và 80 câu nghiệm thu khóa checksum được giữ nguyên.

Đã phát hiện và giữ các attempt sai: nhầm khoản/điểm, thiếu điều kiện đối tượng và dùng QĐ56 đã hết hiệu lực để trả lời quyền tái định cư cá nhân. Bản hiện tại kiểm tra số khoản/điểm, giữ nguyên văn điều kiện nguồn trước semantic verifier, chặn áp dụng quy định lịch sử thiếu chuyển tiếp liên quan. Yêu cầu chắc chắn quyền lợi hộ/thửa phải hỏi hồ sơ, không suy từ tài liệu công khai. Runtime vẫn kiểm chứng trước SSE, công cụ chỉ đọc và giới hạn workflow 6 LLM/12 công cụ/hai vòng/90 giây. Không còn quota LLM/embedding ngày do ứng dụng đặt; quota provider và bảo vệ phiên/IP giữ riêng.

| Mốc | Bằng chứng đạt | Còn lại theo kế hoạch gốc |
|---|---|---|
| M0 | Pages, Render Free, Supabase và provider thật; code cuối live | Đã đạt smoke URL; chưa phải nghiệm thu pháp lý rộng |
| M1 | 69 nguồn, 7.610 vector đầy đủ, audit/locator/quan hệ, archive/parity/restore | Corpus đã công bố; phạm vi nguồn bổ sung còn thiếu vẫn công khai |
| M2 | Hybrid FTS/pgvector/RRF, baseline thật, hội thoại và dẫn nguồn | QA đầy đủ trên corpus công bố; cải thiện retrieval đo được |
| M3 | LangGraph/công cụ/hiệu lực/verifier, sáu ca core đúng cấu hình | Smoke 20 cặp và đánh giá chất lượng rộng hơn |
| M4 | Build, hai Vitest, tám Playwright desktop/mobile; nhãn demo kỹ thuật | QA Pages thật đã đạt; mở rộng tình huống phức tạp theo benchmark |
| M5 | **174 tests** local/CI `38429670145`; Docker Python 3.12 hard 512 MiB, peak **353,55 MiB**; restore PostgreSQL tách biệt, rollback/withdrawal và bảo vệ API đạt | 80 câu nghiệm thu/chấm nguồn; p95 API một người dùng, cập nhật chứng cứ vận hành sau công bố |
| M6 | Repo, Docker, migrations, pipeline, CI/CD, docs và backup mã hóa mới | URL demo đã kiểm chứng; nghiệm thu toàn bộ M0–M6 vẫn pending |

Website https://hanoi-land-law.pages.dev; API https://land-law-chatbot.onrender.com; repository https://github.com/dovh25x/land-law-chatbot. Commit code `5063a43`, fingerprint `b059cbbd`. Gate `reports/technical-release-gate.json` đạt sáu source-reviewed results, audit/runtime checksums đúng. Fresh backup mã hóa trước công bố đã giải mã kiểm tra thành công; bài tập restore PostgreSQL riêng có receipt, không suy một vòng giải mã là diễn tập database restore mới.

Baseline retrieval diagnostic trước sửa guard, cùng index và fingerprint `2126675f`: Recall@8 **0,149122807** trên 57 câu có gold trong 80 câu nghiệm thu; không LLM/fallback. Đây là giới hạn còn tồn tại và không phải điểm agentic hoặc chứng nhận cấu hình cuối. Chưa chứng minh Recall@8≥85%, rubric≥85%, support≥95% và p95≤60s trên nghiệm thu đầy đủ. Không đổi gold/ngưỡng hoặc ghép số liệu model/config khác. Bộ tham chiếu chưa được thẩm định pháp lý độc lập.

Không bật billing/nâng gói. Phiên/trace TTL bảy ngày, token hash, session isolation, CSP/CORS và log không ghi nguyên câu hỏi. CI/tests tách SQLite/FakeProvider khỏi production sau sự cố fixture trước đây; hai corpus thật được bảo toàn. Bằng chứng: `reports/ci.json`, `runtime-tests.json`, `docker-memory.json`, `technical-release-gate.json`, `source-audit.json`, `prepublication-backup.json`, `postgres-restore.json`, `implementation-progress.json`, cùng checkpoint và reviews checksum. Báo cáo cũ/cấu hình khác không chứng nhận bản hiện hành.

Smoke HTTPS: baseline 21,254 giây, agentic 54,244 giây (có retry quota TPM); đây là hai mẫu, không suy p95. Hai đáp án live hỗ trợ bởi Điều104, nhưng chưa nêu riêng thiệt hại khi di chuyển máy móc/dây chuyền; hạn chế đã ghi trong `reports/live-demo.json`, không đưa hai mẫu này vào benchmark S07 như đáp án hoàn chỉnh. `reports/live-ui.json` xác nhận Pages desktop/mobile thật, 69 tài liệu, ba hồ sơ/năm nguồn mỗi dự án, source/PDF link, trace và tải lại lịch sử. Evidence dùng để công bố được lưu bất biến trong `reports/publications/`.

Kiểm tra restart trên Render đã đạt: active corpus, profile technical_demo, hội thoại và trace giữ nguyên sau deploy `3aec924`; API đang phục vụ smoke đúng fingerprint. CI của commit bàn giao `38431929277` đạt. Backup sau công bố chạy thành công trên Actions `38432785890`, artifact `11830823775` (105.897.315 byte, hết hạn 21/10/2026); đây là receipt workflow/artifact, không coi là restore mới. Một ca followup tự nhiên đã thử hai lần và chưa đạt: lần đầu provider Retry-After24s, lần hai đủ sáu LLM/12 công cụ nhưng chưa kết luận. Kết quả limited không có claim/trích dẫn được giữ trong `reports/live-followup.json` và `live-attempts/`; không đánh dấu tính ổn định hỏi tiếp nối đã hoàn tất. Có thể dùng số văn bản/điều rõ ràng trong demo; Cải thiện giải tham chiếu là việc còn mở.
