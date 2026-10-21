# Phase 3A — Controlled Live Model Pilot

**Kết luận: NOT READY để chuyển sang release validation.** C01 bị gián đoạn trong repair; C02/C03 không bắt đầu sau điểm dừng vận hành. Không có ca nào được chứng minh PASS. Pilot đã dừng, không chạy lại, không sửa runtime để tối ưu kết quả.

Chỉ dùng câu hỏi giả lập đã khóa, ngày hỏi **21/10/2026**, nguồn luật công khai trong candidate và SQLite tạm riêng. Không mở database phục vụ, không gọi judge ngoài pipeline, không full evaluation, không commit/push/deploy. S06 giữ FAIL.

**Identity và cấu hình**

| Thành phần | Giá trị |
|---|---|
| Git HEAD | `117e7bd2c4a320c3d02256dfdabf858180b47dbf` |
| Working tree | Có thay đổi từ trước; cả 199 file nguồn khớp Phase2D trước/sau pilot |
| Source-tree SHA256 | `57adb766b39010c3290232899c1e301efd722bf5c1dd5cc1f3a7afc55939c05b` |
| Candidate identity Phase2D | `b90108a76ec7309e81b0e5940fa0027d5a1788485d212de8177f6e37812d897c` |
| Runtime fingerprint SQLite | `37d2fb54ca0ce64d852190df32e7bea80920fd7fce99a7a7624a157185e953a7` |
| Corpus ID | `corpus-1afca764aa6692e0` |
| Corpus payload SHA256 | `7ce7956ae35c7006b5bfd7d10d516fa9e8e47fe2f073e471ceecbb34b412d317` |
| Source-policy canonical SHA256 | `dfe58f8376d4d4d978ace0483ba45a70e60eafa473285ffbe5a6a2a8e7f72dd4` |
| LLM | Groq `openai/gpt-oss-120b`, temperature 0, max completion 2048; reasoning medium cho Draft/Verification, low cho Plan |
| Embedding | E5 ONNX Q8 384 chiều, `multilingual-e5-small-onnx-q8-window-v1`; file model/tokenizer đối chiếu checksum trước chạy |
| Giới hạn | 6 requests/ca, 18 toàn pilot, 60.000 tokens, 90 giây/ca; giữ 12 tools, 2 retrieval rounds, 1 repair |

Local `.env` mặc định bật `allow_stale_generation=true`; runner ghim **false trước mọi attempt** để khớp candidate Phase2D đã duyệt. Không sửa `.env`, không thay cấu hình giữa các request/case, không bypass freshness. Hai database URL được để trống trong đối tượng Settings local và SQLite nằm trong thư mục tạm riêng. [Configuration lock](configuration-lock.json) chứa các input checksum; khóa này được kiểm tra trước mỗi lần gửi mạng. System prompt SHA256 giống nhau ở cả ba request thực gửi. `previous_draft`/`previous_issues` thay đổi theo repair vốn có của pipeline.

**Kết quả và ngân sách**

| Ca | Kết quả cuối | Attempts bắt đầu | HTTP requests | Tokens được Groq báo | Thời gian toàn ca |
|---|---|---:|---:|---:|---:|
| C01 — Bồi thường | **INCOMPLETE**; draft đầu không đạt kiểm chứng | 1 | 3 | 4.829; hai phản hồi lỗi thiếu usage | 34,858 giây |
| C02 — Hỗ trợ | **INCOMPLETE**, chưa chạy do dừng sau C01 | 0 | 0 | 0 | Không có |
| C03 — Tái định cư | **INCOMPLETE**, chưa chạy do dừng sau C01 | 0 | 0 | 0 | Không có |

Không gán FAIL nội dung cho ca chưa chạy; cũng không gán PASS dựa trên fixture trước đó. C01 là gián đoạn vận hành trên một câu hỏi có căn cứ, không phải từ chối đúng vì thiếu nguồn. Không tính Answer Correctness hoặc False Abstention Rate từ pilot chưa hoàn tất này.

| Request C01 | Giai đoạn / kết quả | Usage báo cáo | HTTP latency | Hành vi tiếp theo |
|---|---|---:|---:|---|
| 01 | Draft, HTTP200; 1 claim bị structural verifier bác | 3.474 input + 1.355 completion = 4.829 | 3.756 ms | Một repair trên cùng chứng cứ |
| 02 | Repair Draft, HTTP429, TPM limit 8.000 | Không có | 148 ms | Tuân thủ Retry-After 4 giây |
| 03 | Retry của repair, HTTP400 `json_validate_failed` | Không có | 4.941 ms | Retry tiếp bị chặn trước mạng |

Khoảng cách ghi nhận từ phản hồi 429 đến request kế tiếp là **4,497 giây**, lớn hơn Retry-After. Header còn 189 tokens và reset 58,582 giây ở phản hồi cuối được lưu nguyên trong receipt; không tiếp tục gọi API. Không gặp timeout 90 giây.

Bộ chặn ở transport dự phòng **số byte UTF-8 của toàn request JSON + 4.096 phần dư framing/schema + 2.048 max completion**, trước từng request kể cả retry. Có usage hợp lệ mới thay dự phòng bằng usage; thiếu usage giữ toàn bộ dự phòng. Sau ba request: **4.829 tokens đo được**, **52.159 tokens tính bảo thủ** gồm hai request thiếu usage. Đây không phải tuyên bố đã thực tiêu 52.159 tokens. Request thứ tư cần dự phòng thêm 23.665, tổng sẽ là **75.824 > 60.000**, nên bị chặn trước mạng. Không nới ngân sách sau khi thấy kết quả. Runtime ghi `llm_calls=4` vì tăng bộ đếm trước transport; số HTTP thực gửi là **3**, không phải 4. [Blocked request](C01/blocked-request.json), [budget](budget.json).

**Context thực gửi và citation integrity**

Ba request thực gửi đều có **8 synthesis sources**, **6.697 ký tự** cho JSON `[evidence, documents]` theo cùng cách đo runtime; đủ **4/4 đoạn bắt buộc C01**. Full request gồm thêm instruction, schema và metadata; 7.000 ký tự không phải giới hạn toàn HTTP body.

| Alias | Nguồn trong synthesis snapshot |
|---|---|
| C1 | Luật 31/2024/QH15, Điều95 khoản1 điểm a: nhóm hộ/cá nhân, không thuê trả tiền hằng năm |
| C2 | Luật31, Điều95 khoản2: dẫn khoản1 và các điều kiện thay thế; scope dependency trỏ C1 |
| C3 | NQ254/2025/QH15, Điều3 khoản10: loại trừ bồi thường |
| C4 | Luật31, Điều98 khoản1: chủ thể, đủ95, các hình thức bồi thường |
| C5 | Luật31, Điều111 khoản4: nhóm và điều kiện tái định cư/hỗ trợ riêng |
| C6 | Luật31, Điều108 khoản1: các nhóm hỗ trợ |
| C7 | Quy định kèm QĐ40/2026/QĐ-UBND, Điều21 mở đầu và khoản1: phạm vi/phường |
| C8 | Quy định kèm QĐ40, Điều21 khoản2/3: xã và ngoại lệ |

Retrieval diagnostics ghi **36 candidate IDs** từ search/open/parent expansion, retained **16**, source admission cho phép **14**, context synthesis chỉ **8**. Đây là các tập khác nhau, không coi retrieved là được phép cite. Hai nguồn retained nhưng không admitted là Luật2013 và QĐ56/2024; chúng không xuất hiện trong synthesis. Raw source IDs, checksum, scope dependency, admission và lý do loại nằm tại [source-state request01](C01/wire/01/source-state.json). Trạng thái retrieval diagnostics là sổ theo ID sau expansion, không phải Recall@5.

Draft đầu dùng C1,C2,C4,C5,C7; tất cả đều thuộc synthesis snapshot. **Điều này chỉ đạt ràng buộc nguồn hiện diện, không chứng minh citation hỗ trợ mọi kết luận.** C3 được gửi đầy đủ nhưng model không cite C3 cho mệnh đề về NQ254. Không phát hành claim hoặc citation nào ra người dùng.

Payload thực gửi được chụp tại transport ngay trước HTTP, không phải chỉ intermediate context: [request01](C01/wire/01/request.json), [request02](C01/wire/02/request.json), [request03](C01/wire/03/request.json). Mỗi thư mục có source-state và response. Headers Authorization không được ghi.

**Review nội dung C01 và kết quả verifier**

Đối chiếu đoạn nguồn thực gửi với [review pháp luật Phase2C đã khóa](../phase2c-current-20261021/LEGAL_REVIEW.md), không thay gold hoặc luật tham chiếu:

- Draft viện dẫn khoản10 Điều3 NQ254 nhưng thiếu citation C3. Đây là lỗi có căn cứ độc lập với lỗi kiểm tra chủ thể.
- Draft rút nhánh Điều111(4) thành “trường hợp không đủ diện tích” nhưng bỏ nhóm nhiều thế hệ/nhiều cặp vợ chồng hoặc nhiều hộ chung quyền và các điều kiện tương ứng. Không đủ để phát hành như quy tắc chung.
- Draft đưa công thức bán căn hộ/giao đất nếu đủ quỹ đất của QĐ40 Điều21(1) mà bỏ phạm vi **phường**, không giữ nhánh **xã** riêng. Câu trả lời mở rộng thêm nội dung không được hỏi và làm mất điều kiện.
- Về OR/AND: draft có chủ thể không thuê trả tiền hằng năm kết hợp với GCN **hoặc** quyết định giao đất. Không quan sát thấy biến OR thành AND tại phần này; chưa thể coi toàn câu trả lời đúng hoặc xác nhận repair đúng.

Structural verifier kết luận **0/1 claim supported**, hai issues: thiếu diễn đạt quan hệ với khoản1 và số văn bản không được citation chứng minh. Issue đầu phụ thuộc regex đòi cách diễn đạt có “khoản1”; draft thực đã nêu hộ/cá nhân và điều kiện không thuê hằng năm. Vì vậy **không dùng riêng issue đó để khẳng định model sai chủ thể**. Các lỗi citation và thiếu điều kiện nêu trên vẫn tồn tại. Không chỉnh guard, prompt, heuristic hoặc tối ưu F03/S06 trong pilot.

Không có request model-verifier: structural verifier đã bác draft đầu trước bước đó. Repair không trả được JSON hợp lệ để verify tiếp. [Attempt và verifier verdict đầy đủ](C01/attempt.json); [raw response hiển thị đầu](C01/wire/01/response.json), [429](C01/wire/02/response.json), [400](C01/wire/03/response.json).

Final answer thực tế: **“Lượt hỏi đã đạt giới hạn thực thi. Hãy tách câu hỏi hoặc thử lại.”** Status `limited`, `verified_claims=[]`, `citations=[]`. Không coi đây là đáp án đúng cho C01 và không thực hiện gợi ý “thử lại”.

**Phần chưa kiểm chứng và giới hạn artifact**

- C02/C03 chưa gửi request. Số context **5.070/6.981 ký tự** và completeness của hai ca đó thuộc **Phase2D deterministic capture**, không phải live-model result Phase3A. Đặc biệt C03 sát 7.000 ký tự vẫn chưa được kiểm chứng qua Groq.
- Response thành công lưu nguyên nội dung hiển thị của model, usage và metadata; không lưu suy luận ẩn. HTTP400 chỉ giữ error metadata và SHA256 toàn body; trường `failed_generation` không được lưu. Không thể review hoặc tái dựng nội dung repair lỗi từ artifact, và không gọi lại để bổ sung.
- Hai lỗi HTTP không báo usage: tổng token thực tiêu không xác định đầy đủ; con số bảo thủ được phân biệt với số đo.
- SQLite không chứng minh tương đương PostgreSQL. Deployment fingerprint, public E2E và các điều kiện release còn thiếu từ Phase2D chưa được xác minh ở đây.
- Receipt nguồn chỉ cho ngày hỏi21/10; không tự mở scope sang ngày nộp23/10.

**Kiểm tra và bảo toàn**

Đã chạy **8/8 tests offline cho runner**, không gọi API: reserve/refund theo usage, thiếu/usage không hợp lệ, vượt bound, chặn60.000 trước transport, 6/18 requests, capture payload thực và loại nội dung suy luận ẩn. Command và kết quả ở [offline preflight](offline-preflight.json). Không chạy lại 486 backend tests: đó là kết quả **Phase2D**, không phải số mới của Phase3A; runtime không thay đổi ở vòng này.

Post-run kiểm tra HEAD,199 file nguồn, corpus, cases, policy, receipts và runner theo SHA256 đều giữ nguyên; status working tree cũ giữ nguyên, chỉ thêm thư mục báo cáo Phase3A. [Technical review](technical-review.json), [execution receipt](execution.json), [baseline](baseline.json). Chạy lại `review_pilot.py` chỉ đọc artifact để dựng review, không gọi model. `runner.py --live` có marker độc quyền chống tự chạy lại và không được gọi lại.

`scripts/check_secrets.py` PASS; kiểm tra riêng mọi file artifact dạng text với secrets đang cấu hình cũng PASS, không in giá trị secrets. [Kết quả scanner](secrets-check.log), [chỉ mục checksum artifact](artifact-index.json).

**Quyết định tiếp theo để review**

Chưa đủ bằng chứng chuyển sang release validation: C01 chưa phát hành được đáp án có kiểm chứng; C02/C03 chưa thử. Đề nghị review riêng các lỗi đã ghi nhận và chính sách ngân sách/khả năng vận hành trong TPM8.000 trước khi cấp bất kỳ quyền sửa hoặc pilot tiếp theo. Nếu chọn kế hoạch mới, cần phê duyệt riêng; không nối tiếp vòng hiện tại hoặc chạy lại để chọn kết quả đẹp. Các attempt thất bại và S06 được giữ nguyên.
