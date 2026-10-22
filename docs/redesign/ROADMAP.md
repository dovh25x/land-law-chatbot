# Lộ trình triển khai có thể review

> **Design record — historical.** Tài liệu này được viết trước khi bounded Agentic RAG lên production; các đoạn nói về planner/verifier/repair, budget 6/12/2/1 hoặc schema-2 có thể không còn đúng. Runtime hiện hành: [AGENTIC_RAG.md](../AGENTIC_RAG.md) và [ARCHITECTURE.md](../ARCHITECTURE.md).


Đây là kế hoạch được lập trong đợt thiết kế; tiến độ thực tế nằm tại [IMPLEMENTATION](IMPLEMENTATION.md). Giới hạn không sửa runtime/prompt ở đợt thiết kế đã kết thúc khi chủ dự án yêu cầu triển khai; bộ khóa và artifact lịch sử vẫn giữ nguyên. Ưu tiên từng lát chức năng hoàn chỉnh có nguồn, giao diện và phép đo; không gom thành một lần viết lại agent.

## Thứ tự và điều kiện hoàn tất

| Giai đoạn | Đầu ra cụ thể | Điều kiện hoàn tất | Phụ thuộc |
|---|---|---|---|
| 0. Khảo sát và thiết kế | Bộ tài liệu này, inventory, draft scenarios/journeys | Phân biệt hiện trạng/thiết kế, phạm vi đã chốt; checksum suite cũ nguyên vẹn | Đã chuẩn bị trong đợt này |
| 1. Kiểm chứng nhu cầu và nguồn | Phỏng vấn ngắn, ma trận C01–C12 có người phụ trách, danh sách coverage theo hành trình | Nhu cầu ưu tiên có bằng chứng hoặc giữ nhãn giả thuyết; biết nguồn còn thiếu | Sản phẩm/nguồn/người nghiên cứu |
| 2. Annotation và hợp đồng | Bộ dev v2 được legal/content review; schema/compatibility test; handoff Figma trên hệ thiết kế hiện có | Freeze trước prompt; bố cục và nội dung được review; chưa gán điểm cho draft | 1 |
| 3. Nhu cầu và câu trả lời dễ hiểu | Xử lý hỏi vừa đủ, trường cấu trúc và renderer cùng claim đã verify | Regression mất điều kiện không tái phát; không có post-verify paraphrase; đọc lịch sử cũ được | 2; nguồn nền sẵn có |
| 4. Giấy tờ và nơi liên hệ | Nguồn procedure/directory đã duyệt, policy vai trò/freshness, các lát tác vụ đủ nguồn | Checklist/đầu mối đúng nguồn và phạm vi, thiếu nguồn xử lý rõ, roundtrip hai backend | 2; không cần chờ mọi nguồn toàn dự án |
| 5. Đánh giá và sửa lỗi | V2 dev/journeys + legacy liên quan, holdout tương lai, hai vòng usability | Báo cáo đủ mẫu số/attempt; giữ fail, không trộn cohort; biết giới hạn còn lại | 3–4 |
| 6. Phát hành từng phần | Release corpus, source SHA, rollout capability, live checks, rollback | Kiểm tra phần mềm/nguồn/restore/identity thực; công bố rõ chất lượng và phần chưa xác minh | 5; quy trình vận hành hiện có |

Ước lượng lập kế hoạch ban đầu là 5–7 tuần lịch với một kỹ sư, reviewer pháp lý/nội dung có thời gian làm việc đều và người phụ trách nghiên cứu/thiết kế. Đây là giả định nguồn lực, không cam kết; OCR, quyền tiếp cận người dùng và lịch reviewer có thể chi phối. Tuần đầu phải điều chỉnh ước lượng theo số nguồn/tác vụ đã đọc thật. Vai trò không nhất thiết là các nhân sự toàn thời gian riêng.

## Các patch đề xuất

| Patch | File/module chính | Hồi quy phải có |
|---|---|---|
| V2-01: registry bộ đánh giá | `evaluation.py`, `cli.py`, exporters, readiness, `data/evaluation/` | Ba checksum/count cũ không đổi; draft không chạy như frozen; metadata/prompt/suite mismatch bị từ chối |
| V2-02: nhu cầu và hỏi làm rõ | `models.py`, `agent.py:plan`, module nhu cầu nhỏ nếu cần | Không hỏi hồ sơ cho câu định nghĩa; “giấy thu hồi” không tự thành quyết định; ngôi “tôi” không tự chặn câu chung; sửa dữ kiện/hết history |
| V2-03: claim và phần trả lời | `models.py`, `provider.py`, `agent.py:synthesize/verify/finish`, `api.py` | Mọi action nằm trong verify; OR/AND, chủ thể/điều kiện, verdict mâu thuẫn, index mồ côi; veto cả nhóm giữ nguyên |
| V2-04: UI theo tình huống | `App.tsx`, `ui.tsx`, `api.ts`, `history.ts`, CSS hiện có, e2e | Gợi ý không tự gửi; một câu làm rõ; “không biết”; nguồn của đúng claim; focus/mobile/IME; cũ/mới tương thích |
| V2-05: nguồn tác nghiệp | `models.py`, `ingest.py`, `security.py`, `catalog.py`, `store.py`, `ops.py`, policy/fingerprint, manifest | Directory không chứng minh thẩm quyền; news không thành checklist; sai địa bàn/ngày/conflict/quá hạn chặn action; domain allowlist/redirect |
| V2-06: chỉ mục và phát hành nguồn | Candidate/audit/package/restore scripts, release metadata | Vector không đổi giữ nguyên; dependency closure; gold v2 có mapping, gold cũ không sửa; restore DB riêng, runtime role |
| V2-07: trải nghiệm gián đoạn | Frontend trạng thái và projection nguồn | AI quota không chặn đọc nguồn nếu API sẵn sàng; DB lỗi nói chưa tải được; không replay POST; không có static đáp án AI giả |
| V2-08: đo và công bố | Evaluation/export/public reports, `EvaluationPage.tsx`, `evaluationHighlights.ts` | Cấu hình không khớp không đại diện v2; không bỏ fail/not_run; dữ liệu người thật không lên reports; rubric không tự thành cổng deploy |

Đường V2-02/03 thực hiện bên trong graph hiện có. Module nhỏ giúp schema/policy có thể kiểm thử không phải lý do di chuyển toàn bộ agent. Mỗi bug cần case tái hiện trước, patch nhỏ và chạy kiểm tra phù hợp; không viết test chỉ kiểm tra văn bản prompt chứa một câu mới.

## Lát đầu tiên nên triển khai

Hoàn thiện hành trình “vừa nhận giấy nhưng không biết bắt đầu”: vào được từ trang chủ, chọn/nhập tên giấy hoặc không biết, được giải thích chung có nguồn, biết thông tin cần đọc, không bị xin ảnh/định danh, mở được căn cứ. Dùng nó để kiểm tra schema/hỏi làm rõ/renderer/verify trước khi thêm directory.

Lát thứ hai là “cần chuẩn bị giấy tờ cho một việc cụ thể”, chỉ phát hành nhánh có đủ nguồn thủ tục đã duyệt. Lát thứ ba là đầu mối và bất đồng/khiếu nại; không mở chức năng hướng dẫn nộp cụ thể trước khi có nguồn thẩm quyền + directory + freshness. Có thể công bố phần tra cứu nguồn và giải thích chung trong khi các nhánh này còn thiếu.

## Giữ và bỏ khỏi thiết kế vận hành mới

| Giữ | Thay thế hoặc bỏ vai trò cũ |
|---|---|
| Pipeline, provider/embedding contract, budget, ingress, quota, privacy | Cách mở đầu đòi người dân tự đặt câu hỏi chuyên môn |
| Corpus/raw có xuất xứ và những phần đã đúng | Taxonomy theo văn bản làm điểm vào duy nhất |
| Guard về nguồn, điều kiện, hiệu lực và veto cả nhóm | Khối `missing_facts` dài làm trải nghiệm hỏi lại mặc định |
| Figma tokens/components, responsive, sources drawer, lịch sử tại client | Cách trình bày đáp án một đoạn điều luật mà thiếu bước tiếp theo có nguồn |
| Bộ khóa cũ và mọi báo cáo/attempt lịch sử | Dùng tỷ lệ regression hoặc điểm cao nhất lịch sử làm chứng nhận chất lượng v2 |
| Rollback corpus một dự án và không lưu hội thoại | Bất kỳ thành phần mới nào yêu cầu upload, đồng bộ hồ sơ, GIS hoặc vượt phạm vi đã chốt |

“Bỏ” ở đây là bỏ cách dùng/hành vi khỏi phiên bản mới sau khi có replacement được kiểm tra; không xóa archive, Release hay database đang phục vụ trong đợt thiết kế.

## Kiểm tra và rollout

Các lệnh nền giữ nguyên:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Thay nội dung/prompt/corpus cần model evaluation liên quan với suite đã freeze; thay UI cần test trải nghiệm và người dùng, không coi tất cả là fixture. Không chạy model để lấy điểm tốt trong giai đoạn chỉ thiết kế. Kiểm tra cold start, SSE và Turnstile production là phạm vi riêng, chỉ ghi pass khi quan sát thật.

Backend hỗ trợ `content` cũ trước; client dùng schema mới theo capability và feature flag; sau đó mới bật các nhánh nguồn đã đủ. Đánh giá phải ghi đúng code SHA, corpus ID, backend, fingerprint policy và UI. Không công bố điểm mô hình trên SQLite như điểm production PostgreSQL, không ghép kết quả của hai code SHA thành một cohort.

Corpus mới được đóng gói/tải lại/verify/restore vào DB riêng. Nếu cần chuyển kết nối, giữ cấu hình cũ ở nơi chứa secret được bảo vệ, không ghi URL vào artifact. Chỉ gỡ Release cũ sau phát hành và restore đạt. Nếu rollback UI, lịch sử v2 phải đọc được bằng `content`; nếu rollback backend, tắt capability v2 và giữ client fallback. Không rollback về lưu hội thoại server hoặc corpus đa dự án.

## Rủi ro và cách giải quyết

| Rủi ro | Cách xử lý |
|---|---|
| Viết dễ hiểu làm mất điều kiện | Diễn giải nằm trong draft và được verify; teach-back phát hiện hiểu lầm; không rút gọn sau verify |
| Nguồn tác nghiệp thay đổi nhanh | Review có thời điểm và chức năng; chặn action không đủ freshness, không đổi receipt cho tiện |
| Hỏi quá nhiều làm người dân bỏ cuộc | Ưu tiên một dữ kiện; “không biết”; chặn vòng hỏi lặp; đo abandonment trong nghiên cứu có đồng thuận |
| Chặn quá mức dù có nguồn | Đo false abstention trên answerable; tìm lỗi retrieval/context/generation/verifier riêng; không nới guard theo điểm tổng |
| Benchmark mới bị học theo | Bộ dev có nhãn rõ; holdout do người khác làm và khóa trước prompt cuối; giữ mọi attempt |
| Thiếu reviewer/OCR | Thu hẹp lát phát hành; ưu tiên nguồn cho tác vụ quan trọng; không duyệt hàng loạt |
| Free provider/cold start | Nội dung ngắn có trọng tâm trong budget hiện tại, trạng thái đúng thực tế, nguồn không phụ thuộc generation khi backend sẵn sàng |

## Quyết định còn cần bằng chứng

Từ người dùng thật: các điểm vào có được hiểu đúng không, nhãn trạng thái nào ít gây hiểu nhầm, độ dài phù hợp và bao nhiêu lượt làm rõ chấp nhận được. Từ reviewer nguồn: thủ tục/địa bàn nào đủ bằng chứng phát hành, phụ thuộc nào phải đọc thêm. Từ implementation: contract mở rộng có nằm trong budget và tài nguyên hiện tại không. Không cần chọn model/hosting mới để bắt đầu những bước này.
