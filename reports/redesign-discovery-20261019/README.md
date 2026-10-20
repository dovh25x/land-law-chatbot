# Khảo sát và thiết kế lại — 19/10/2026

Đã chuẩn bị [bộ thiết kế v2](../../docs/redesign/README.md) theo lựa chọn của chủ dự án: thiết kế đầy đủ và lộ trình triển khai trước, ưu tiên thủ tục, giấy tờ, nơi liên hệ và khiếu nại của người dân liên quan Vành đai 4 Hà Nội. Không thay runtime/prompt, không ingest/embedding, không chỉnh active corpus hoặc deploy trong lần này.

## Phạm vi khảo sát

Đọc tài liệu README, PRD, kiến trúc/agent flow, API, frontend/handoff, đánh giá, vận hành và ADR; đọc các module runtime backend; xem luồng hội thoại, nguồn, history/ingress và cách công bố evaluation phía frontend; đối chiếu migrations, CI/deploy, helper ingest/candidate/audit/đánh giá/restore và các nhóm kiểm thử. Đọc các suite đã khóa và các báo cáo corpus, remediation, readiness, phát hành và hoàn thiện sản phẩm gần đây.

[source-inventory.json](source-inventory.json) kiểm kê toàn bộ file tracked và ghi checksum/outline cho source, tests, scripts, docs và cấu hình trong phạm vi khảo sát. Inventory không có nghĩa mọi report lịch sử, binary, PDF/ảnh và vector đã được đọc/rà soát thủ công. Raw pháp lý chỉ được đối chiếu ở mức provenance/metadata/đoạn minh họa cần thiết; không thực hiện lại thẩm định pháp lý toàn corpus, OCR toàn bộ, vector audit hoặc kiểm tra tài khoản hosting/provider.

[Bản đồ công nghệ và công cụ](TECHNOLOGY.md) ghi rõ các lớp runtime, retrieval, ingest/OCR, dữ liệu, UI, kiểm thử, phát hành và nguồn thiết kế đã đối chiếu, cùng những contract ảnh hưởng đến v2.

## Identity phải phân biệt

| Nguồn quan sát | Ghi nhận trong lần khảo sát |
|---|---|
| Source checkout ban đầu | `fefee29` (full SHA trong inventory); working tree sạch trước thay đổi |
| SQLite local, mở read-only | `corpus-581da76c79b0b362`, 59 tài liệu, 7.555 chunk; 54 legal, 1 project decision, 4 news; 98 relations, 4 unresolved, 5 coverage gaps |
| Manifest hiện tại | 68 entries, 60 `verified`, 8 `pending`; nhãn manifest không tự chứng minh tất cả nằm trong local hoặc production |
| Package phát hành ngày 19/10 trong workspace | `corpus-a26bc99e541fbbe2`, 60 tài liệu, 7.392 chunk; không đồng nhất với local DB |
| Báo cáo hoàn thiện sản phẩm gần đây | Ghi nhận production dùng corpus mới và generation snapshot override; đây là bằng chứng đã lưu, không phải live check mới trong lần thiết kế |
| Bộ khóa | Smoke 20 + supplemental 4 + natural 8; checksum xác minh lại trong inventory |

Số lượng ở bảng là quan sát có phiên bản, không được chép thành cam kết coverage trong PRD. [Báo cáo phát hành](../restricted-release-20261019/README.md) và [báo cáo hoàn thiện sản phẩm](../product-completion-20261019/README.md) phản ánh các thời điểm/cấu hình khác nhau. Quy tắc publish/deploy hiện hành đã thay đổi sau một số báo cáo readiness; cần đọc code/runbook hiện tại, không xem một đoạn lịch sử là quy trình hiện hành.

## Phát hiện và quyết định thiết kế

| Phát hiện | Bằng chứng | Quyết định |
|---|---|---|
| Trang đầu vẫn cần người dùng tự đặt câu hỏi; gợi ý chủ yếu theo khái niệm pháp lý | `frontend/src/App.tsx`: `suggestions`, `welcome`, composer | Điểm vào theo tình huống và “không biết”, vẫn giữ nhập tự do |
| Một số yêu cầu quyền lợi riêng bị chặn trước retrieval và kèm danh sách nhiều dữ kiện | `agent.py`: `private_entitlement_check`, `tools`, `synthesize` | Giữ chặn bảo đảm riêng nhưng cho giải thích chung có nguồn; hỏi từng dữ kiện có ích |
| Nội dung synthesis ưu tiên từ vận hành của nguồn và claim ngắn; finish tự dựng đoạn văn từ claims | `agent.py:synthesize/finish`, `models.py:Draft` | Dễ hiểu phải được tạo trước verify; thêm phần cấu trúc tham chiếu nguyên văn claim được duyệt |
| `next_steps` có kiểm tra trong verifier nhưng không có citation/typing riêng như claim | `Draft.next_steps`, `verify`, `finish` | Hành động pháp lý/tác nghiệp phải thành claim có nguồn; không dùng lời hướng dẫn chung làm đường vòng |
| Retrieval đã có alias đời thường, RRF, article headings, mở quan hệ và parent | `retrieval.py`, `store.py`, `agent.py:tools/prompt_context` | Mở rộng có đo theo tác vụ, không thay toàn retrieval hoặc thêm reranker |
| Có luật khiếu nại và phân quyền; source kinds chỉ legal/project_decision/news | `data/sources.json`, `models.py:Document`, `applicability()` | Bổ sung policy và nguồn thủ tục/danh bạ, không tuyên bố thiếu hoàn toàn luật khiếu nại |
| Topics rộng ở một số văn bản; chưa có ma trận đáp ứng việc người dân cần làm | Manifest và `ingest.coverage()` | Coverage theo proposition/hành trình và phụ thuộc; không đo bằng số tài liệu/topics |
| Bộ cũ chứa nhiều viện dẫn điều/số hiệu và kiểm tra giới hạn; natural chỉ là regression nhỏ | Ba JSONL và `docs/EVALUATION.md` | Giữ nguyên bộ khóa, tạo dev/journeys mới và nghiên cứu hiểu biết; không gọi điểm cũ là chất lượng v2 |
| Raw recall và việc chặn claim sai chưa bảo đảm trả lời được nhu cầu | Các review S06/X02/X03/N02/N04 qua nhiều cohort | Tách retrieval, nội dung, false abstention và bước tiếp theo; không nới guard để tăng điểm |
| UI kỷ lục chọn maximum từ archive có provenance | `evaluationHighlights.ts` | Bỏ vai trò đại diện v2 của điểm max lịch sử; archive vẫn nguyên vẹn và xem được |
| Freshness có snapshot override; server history đã bị cấm | `source_fresh`, `Agent.run`, migration 006, runbook | Giữ privacy và cơ chế hiện hành; đề xuất policy action chặt hơn ở v2, không tự đổi cờ |

Các phát hiện là review kỹ thuật/sản phẩm, chưa phải nghiên cứu người dùng hoặc thẩm định pháp lý độc lập. Không có căn cứ kỹ thuật để loại bỏ toàn bộ raw/vector/source còn đúng. Những phần cũ không phù hợp được thay trong thiết kế đích, giữ bằng chứng lịch sử để truy nguyên.

## Đầu ra mới và trạng thái

- Sáu tài liệu thiết kế: sản phẩm, hệ thống, corpus, đánh giá, lộ trình và trang điều hướng.
- 48 câu phát triển và 8 script hành trình, kèm manifest checksum: `draft_not_frozen`, `execution_ready=false`. Chưa có legal gold, fixture/harness hoàn chỉnh hoặc holdout độc lập.
- Liên kết từ README/docs để tìm bản thiết kế, phân biệt rõ với implementation hiện tại.
- Không thay file nguồn, `.env`, CI, migration, manifest vận hành, bộ khóa hoặc artifact lịch sử. Không gọi model, không đánh giá Groq/production hoặc tạo Figma handoff mới.

## Kiểm tra

[verification.json](verification.json) ghi lệnh, exit code, phạm vi và checksum log. Backend 259 tests, frontend unit 10 tests, build và E2E 88 tests đạt trên nền source hiện có. Đây là kiểm tra phần mềm, không phải xác nhận nội dung thiết kế đã được triển khai hay v2 đạt chất lượng.

Attempt backend đầu trong sandbox bị treo sau hai test và đã dừng; E2E đầu không khởi động được webServer. Chạy lại ngoài sandbox đã đạt. Giữ cả log lỗi/dừng và log đạt, không lấy lỗi môi trường làm kết quả pass. Kiểm tra cuối xác minh JSONL/manifest/link nội bộ và checksum ba suite cũ; quét secret sau khi thêm artifact.

Chưa làm: legal/source annotation v2, freeze chính thức, nghiên cứu người dùng, Figma mới, chỉnh prompt/runtime, live chat/Turnstile, benchmark model mới, đo PostgreSQL mới, restore/deploy mới. Những việc đó nằm trong lộ trình, không phải phần còn thiếu của đầu ra thiết kế đã lựa chọn.
