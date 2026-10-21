# Phase 2D — Synthesis Context Integrity & Evidence Completeness

**PASS cho deterministic context/citation integrity; READY để xin phép model pilot C01–C03. NOT READY cho deployment.** Không có model pass trong vòng này. Không gọi Groq/judge API, không commit/push/deploy, không thay production. S06 vẫn FAIL theo attempt cũ.

## 1. Root cause và phạm vi sửa

Đối chiếu cùng retained evidence với code Phase2C được giữ ở `baseline/backend/landlaw/agent.py`: cả ba ca đã retrieval/admit được các căn cứ cần thiết. Chúng mất sau đó ở `prompt_context()`, không phải do thiếu corpus/embedding:

1. Parent thay child trước khi đóng gói. ID child không còn được expose dù văn bản của nó có thể nằm trong parent. Fixture cũ vẫn dùng ID thô ngoài allowed aliases.
2. Ranking độc lập từng passage và kiểm budget kiểu greedy không giữ chuỗi điều gốc–sửa đổi–ngoại lệ. Các đoạn cùng vấn đề hoặc metadata quan hệ lặp lại chiếm budget trước nguồn ít similarity hơn.
3. Budget cũ tính JSON có khoảng trắng và ID thô, khác serialization compact/C aliases thực gửi Groq. Bản vá giữ **7.000 ký tự serialized evidence+documents**, tính đúng representation thực, gồm clause/scope metadata. Đây không phải 7.000 tokens và không phải toàn bộ system/question payload.
4. Verifier mở lại mọi citation từ retained retrieval; finish không biết model đã được cung cấp nguồn nào. Nguồn chỉ có trong retrieval có thể được fixture/judge duyệt sau synthesis.

Luồng sau sửa: retrieval/relations/parent → evidence cap 8+8 → admission hiện có → packing theo article và quan hệ có metadata → source views gửi synthesis → snapshot exposure của lượt hiện tại → structural/semantic verification trên proof đã expose → finish kiểm lại exposure/proof/freshness.

Packing ưu tiên quan hệ amends/repeals theo phạm vi/thời điểm, guides và các article liên quan trước đoạn lặp. Khi cần, chọn các khoản đánh số có sẵn trong source; giữ các dẫn chiếu nội bộ tới điều kiện/ngoại lệ, không gán dẫn chiếu bên trong trích dẫn sửa đổi sang khoản của văn bản sửa đổi. Chỗ lược giữa các phần có dấu `[…]`. Không tóm tắt luật hoặc sửa raw source. Các trường hợp mơ hồ/chưa kết thúc dùng nguyên passage hoặc bị loại vì budget. Quan hệ document trong representation compact dùng chỉ số zero-based, **không chứng minh sửa đổi toàn văn**; phạm vi phải đọc từ đoạn nguồn.

Không tăng context window, số request, repair, tools, retrieval rounds hoặc timeout. Không đổi prompt instructions, OR/AND guard, provider/model, embedding, corpus, receipts, gold answers hay migration. Admission dùng lại chính sách hiện có; stale snapshot hợp lệ của nhánh legacy không trở thành phép vượt known-changed/unknown hoặc scoped gate.

## 2. Evidence trước/sau

[So sánh có kiểm soát](before-after.json) chạy packer cũ và mới trên **cùng evidence thực** của từng ca. [Payload capture](acceptance-locked/report.json) ghi input thực tại `generate(Draft, ...)`, không dựng đáp án pháp lý hoặc semantic judge để tạo pass.

| Ca | Thiếu ở packer cũ | Sau sửa: các đoạn yêu cầu | Ký tự evidence+documents thực gửi |
|---|---|---|---:|
|C01|NQ254 khoản10 Điều3|Luật Đất đai: actor khoản1/điều kiện khoản2 Điều95, khoản1 Điều98; NQ254:3(10) có đủ|6.697 / 7.000|
|C02|Nội dung trả lời chính đã có; phần căn cứ thẩm quyền NĐ49:11(6) chưa được gửi|Giữ khoản1 Điều108, nhánh khoản1 Điều17 QĐ40 và có thêm NĐ49:11(6)|5.070 / 7.000|
|C03|Luật Đất đai111(4), NĐ88:11(2), NĐ49:16(3g)|QĐ40:21 phạm vi và khoản2/3; Luật111(4); NĐ88:11(2); NĐ226:7 phần đã review; NĐ49:16(3g) có đủ|6.981 / 7.000|

Mỗi ca có16 retained sources; số admitted lần lượt14/9/12, số passages thật gửi8/5/6. [evidence-stages.json](evidence-stages.json) tách full retrieved/tool+parent candidates, retained sources, admitted sources, synthesis sources/aliases/text checksums, verified/released citations, missing requirements và exclusion reasons. Admission ở đây được đánh giá trên retained sources; nguồn ngoài evidence cap không được coi là đã gửi model hoặc đã bị freshness từ chối.

Cả14 kiểm tra đoạn nguồn của ba ca đạt, ledger khớp payload thật, không có mandatory amendment/repeal dependency bị báo thiếu trong ba bộ context. Đây là completeness theo các đoạn đã review của **ba tình huống đã khóa**, không chứng nhận bao phủ mọi dẫn chiếu hoặc mọi câu hỏi.

Khác biệt với số1/3 ở Phase2C: báo cáo trước chỉ kiểm nội dung các citation của fixture. Phase2D kiểm thêm căn cứ NĐ49 cho C02. Không đổi gold/đáp án để tạo pass và không tính các lần capture chủ động abstain là Answer Correctness/False Abstention.

## 3. Citation invariant và regression reproduction

Mỗi synthesis/repair thay snapshot nguồn đã expose. Citation chỉ hợp lệ nếu ID và nội dung nguồn thuộc snapshot này và đã admission; cùng một parent chứa child không tự biến childID ẩn thành citable. Verifier chỉ nhận source spans của view đã gửi; quote từ phần ẩn trong cùng chunk cũng không được dùng làm proof. Finish bắt buộc có ledger và kiểm lại snapshot, supporting quotes và freshness trước phát hành. Một lời gọi verifier unit riêng không có ledger không thể phát hành citation qua finish. Citation drawer vẫn tham chiếu chunk/locator/URL nguyên bản, không ghi đè nguồn.

[Tái hiện trước/sau](hidden-citation-reproduction-locked.json): cùng SQLite/evidence, draft và judge là test doubles cố ý duyệt childID chỉ có trong retrieval. **Bản cũ answered với child citation; bản mới insufficient_evidence, không citation.** Đây là integrity regression, không model/legal quality. Positive tests cho alias thực sự expose và đoạn có dấu lược vẫn được chấp nhận.

Diagnostics mới chỉ ở state bộ nhớ trong lượt; không thêm persistence server cho hội thoại/trace. Artifacts chứa câu hỏi giả lập và luật công khai.

## 4. Files thay đổi

Hai file có sẵn:

- `backend/landlaw/agent.py`: admission-to-packing, snapshot exposure, verification/finish proof boundary và diagnostics; giữ guard pháp lý hiện có.
- `backend/landlaw/evaluation.py`: thêm `synthesis_context.py` vào runtime fingerprint. Đây là phụ thuộc bắt buộc để sửa packer không thể giữ nhầm fingerprint cũ.

Ba file mới:

- `backend/landlaw/synthesis_context.py`: packer trong pipeline hiện có.
- `scripts/verify_synthesis_integrity.py`: offline actual-input capture; không có tùy chọn bật Groq.
- `tests/test_synthesis_integrity.py`:25 regression cases.

Sáu file unit fixtures được cập nhật khai báo nguồn đầu vào/proof: `tests/conftest.py`, `tests/test_agent.py`, `tests/test_source_review_policy.py`, `tests/test_s06_clause_context.py`, `tests/test_citizen.py`, `tests/test_quality_candidate.py`. Đây là phụ thuộc của invariant publication mới: **finish thiếu ledger phải từ chối**, kể cả khi gọi trực tiếp. Helper không ghi đè snapshot thật đã capture, không được gọi bởi actual-input harness. [AST comparison](unit-fixture-assertions-unchanged.json) chứng minh mọi assertions cũ giữ nguyên; không sửa câu hỏi/gold hoặc quyết định S06.

Thêm thư mục báo cáo này. [Protection](protection.json) xác nhận2.508 file đã có còn lại không đổi, corpus payload/20+4+8/prior reports và HEAD được giữ nguyên. Các thay đổi khác của người dùng được giữ; artifact F01/F03/Phase2B không đổi.

## 5. Kiểm thử thực tế

- Full backend suite: **486 PASS**, Python3.14.4, [log](backend-locked.log). Sau chuẩn hóa checksum fixture, toàn bộ25 tests mới cũng nằm trong fullsuite chốt **25 PASS** [log](backend-locked.log).
-25 cases mới: dependency priority cho nhiều văn bản; base+amend/repeal/override; điều kiện/ngoại lệ và dẫn chiếu; quoted amendment; parent/child; unstructured/incomplete source; thiếu budget; retrieved/admitted nhưng không expose; alias đúng; proof ở phần ẩn; finish không repack; thiếu modifier vẫn từ chối; snapshot vắng; future/unrelated amendment; runtime fingerprint.
- C04 thiếu dữ kiện → clarification_needed; C05 ngoài phạm vi → insufficient_evidence. C06 nguồn mục tiêu chưa review → nguồn đó bị loại khỏi synthesis, capture abstains. Khả năng từ chối draft cố cite nguồn chưa duyệt còn được kiểm bằng scoped-source regression trong fullsuite.
- [Năm controls lịch sử](historical-summary.json): S01 answered, S02 clarification_needed, S03 answered, N07 clarification_needed, N08 insufficient_evidence. Đây là nhánh source-rule/hỏi thêm/từ chối thật, không draft fixture.
- Secret scan và `git diff --check`: PASS.
- Sandbox làm asyncio/to_thread treo; cùng test đạt ngoài sandbox qua cơ chế quyền thực thi chính thức. Lượt bị gián đoạn/timeout và các log fail trung gian được giữ; log chốt là backend-locked. Có một lượt test timeout100ms bị ảnh hưởng khi chạy đồng thời; không đổi timeout/assertion và fullsuite chốt đạt.
- Không chạy lại frontend/build/E2E vì không có thay đổi frontend/API contract. Không chạy PostgreSQL: không có server/client local, không tạo DB trên cloud. Python3.12 chưa chạy lại trong phase này. Không gọi Groq, RAGAS hoặc judge API; không có model latency/faithfulness/correctness mới.

## 6. Candidate và giới hạn

[Release manifest](release-manifest.json) gắn code tree, runtime SQLite đã capture, PG fingerprint chỉ dự kiến, corpus/policy/suite checksums. Base Git vẫn `117e7bd2c4a320c3d02256dfdabf858180b47dbf`; candidate chưa commit, không coi HEAD là SHA chứa patch.

Corpus giữ `corpus-1afca764aa6692e0`; runtime SQLite mới `37d2fb54ca0ce64d852190df32e7bea80920fd7fce99a7a7624a157185e953a7`. Artifact identity và code manifest cũ không được dùng thay cho candidate này.

Còn rủi ro: model có thể diễn giải sai/từ chối dù đủ input; chọn khoản vẫn là heuristic, không chứng minh tất cả dependencies của mọi query; C03 sát budget nên paraphrase/nguồn thêm có thể làm thay đổi selection; phải giữ fail-closed. Nguồn hiện hành chỉ có phạm vi review ngày21/10; không tự kéo dài sang23/10. Các nhánh chưa review, NQ36 và trường hợp đặc thù vẫn có giới hạn của Phase2C. SQLite không chứng minh pgvector/public E2E. S06 FAIL không đổi.

## 7. Quyết định và pilot đề xuất

**READY cho bước xin phép model pilot giới hạn**, xét riêng context/integrity của C01–C03. **NOT READY deployment** cho tới khi có model review, PostgreSQL, pin SHA/corpus/policy/fingerprint và public ingress/SSE/citation E2E. Không gọi mô hình theo quyền chạy offline của phase này.

Pilot: một attempt mỗi C01/C02/C03, tuần tự, câu hỏi/as_of21/10 và corpus/receipts/model/runtime đã khóa. Tối đa6 LLM requests/ca tính planner/synthesis/verifier/repair/retry, tối đa18 toàn pilot;90giây/ca, cooldown/quota hiện có. Không judge service riêng hoặc chạy lại để chọn kết quả. Dự toán phải được trừ vào ngân sách full evaluation được duyệt, không mặc định có ngân sách bổ sung. Ngân sách output theo cấu hình2048 tokens/request: tối đa36.864; **dự toán45–75nghìn total tokens**, không phải benchmark hoặc hard token cap đang được runtime cưỡng chế. Cần người dùng duyệt ngân sách và runner trước khi gọi; capture harness này cố ý không bật được API. Runner frozen-suite hiện có không nhận C01–C03: không sửa gold/registry để lách; sau approval dùng adapter operator một lượt với cùng Agent, SQLite riêng và archive đầy đủ.

Lưu mọi attempt, input sources, aliases/views, output, supporting proof/verdict, usage, latency và fingerprint; đánh giá đủ điều kiện/phạm vi/ngoại lệ/sửa đổi và citation. Từ chối đối với ca answerable phải ghi là chưa đạt answer correctness, không tính đúng. Ba ca này là pilot kiểm chứng coverage hiện hành, không thay câu hỏi hay chọn mẫu cho score của bộ32 đã khóa.

Dừng để người dùng review. Không tự gọi model, commit, push hoặc deploy.
