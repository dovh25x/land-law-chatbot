# Phase 2C — Current Legal Coverage Recovery

**Kết luận: NOT READY cho deployment.** Đã review đủ bộ nguồn cho ba tình huống tại mốc 21/10/2026; **chưa chứng minh pipeline đủ đầu vào synthesis cho cả ba**. Kiểm tra bổ sung phát hiện fixture có thể dẫn ID retrieval không được đưa vào prompt thực tế. Chưa có model pass, PostgreSQL hoặc public E2E cho candidate này. Không gọi Groq, không commit/push/deploy, không đổi production database/credentials. S06 model FAIL cũ và mọi lần thử không đạt được giữ nguyên.

Bản chốt: [release-manifest-reviewed.json](release-manifest-reviewed.json), [acceptance-summary-reviewed.json](acceptance-summary-reviewed.json), [synthesis-projection-review.json](synthesis-projection-review.json), [acceptance-context-pack/report.json](acceptance-context-pack/report.json). `release-manifest.json`, `release-manifest-final.json` và các checkpoint trước giữ nguyên làm bằng chứng; manifest reviewed bổ sung blocker projection trên cùng identity code/corpus.

## 1. Ba tình huống, điều khoản và bằng chứng

Ngày hỏi là21/10/2026. Cả ba là tình huống giả lập Vành đai4 theo chế độ chung, không tự suy cơ chế258/90, không phương án/hồ sơ cũ hoặc quyết định chọn chế độ chuyển tiếp. Không xác nhận quyền của một hộ thật. Các giả định và đáp án kỳ vọng đầy đủ ở [acceptance-cases-final.json](acceptance-cases-final.json).

| Ca | Đầu vào quyết định | Căn cứ đã đối chiếu | Kết quả cuối |
|---|---|---|---|
|C01 — điều kiện bồi thường|Hộ sử dụng đất ở không thuê trả tiền hằng năm; GCN hợp lệ, sở hữu nhà gắn QSDĐ; thu hồi công cộng; không loại trừ/phương án cũ|Luật31:95(1a)/(2a),98(1); NQ254:3(10), chuyển tiếp3(13)/13(3)|**Structural fixture PASS**, nhưng synthesis thiếu NQ254:3(10); chưa đạt đầy đủ pipeline. **Model chưa chạy**.|
|C02 — hỗ trợ|Đất nông nghiệp đủ điều kiện bồi thường; mất40% cùng xã theo riêng dự án, không cộng dồn; không di chuyển; không phương án cũ|Luật31:108; QĐ40 Quy định17(1a/b); NĐ88:19 cùng226:2(4),49:11(6)|**Structural fixture PASS**; nội dung cần thiết có trong prompt qua parent cùng điều. Fixture dùng childID không được expose nguyênID; chưa model/E2E pass.|
|C03 — tái định cư|Hộ ở xã, đất ở/nhà gắn QSDĐ đủ95; thu hồi hết/phải di chuyển/không còn nhà đất khác cùng xã; không nhà nhà nước/chế độ đặc thù/phương án cũ|NĐ88:11(2a); đúng gạch thứ5 điểm a khoản2 Điều7 NĐ226 cùng49:16(3g); Luật31:111(4); QĐ40 Quy định21(1–3)|**Structural fixture PASS**, nhưng synthesis thiếu NĐ88 và NĐ49; chưa đạt đầy đủ pipeline. **Model chưa chạy**.|

[Bảng review pháp luật, quan hệ, nguồn chính thức và giới hạn](LEGAL_REVIEW.md). Các PDF/ảnh được tải lại và kiểm nội dung, không cấp fresh chỉ từ HTTP200/checksum. Có74đoạn được duyệt theo các khoảng ngày, trong đó43đoạn được phép tại21/10; không duyệt cả60văn bản. Whole-corpus vẫn59stale+1unknown. Chỉ dùng [receipts-final](receipts-final/) và [source-gate-final.json](source-gate-final.json).

NQ36/2026/NQ-HĐND là gap có thật: đã xem bản ký do trường công lập đăng lại, nhận ra trang đăng ghi sai ngày hiệu lực so với bản ký01/07. Chưa có nguồn được allowlist runtime chấp nhận để index/cite; không mở các nhánh nhà nhà nước, công trình không hợp pháp, tái định cư khác. Ba ca ở trên loại trừ các nhánh này. Không coi review phạm vi này là thẩm định pháp lý độc lập.

## 2. Corpus/retrieval đã sửa

Giữ nguyên60document và mọi metadata/chunk/vector cũ. Candidate thêm **4đoạn nguyên văn**, chỉ E5local cho4vector mới, không embedding lại corpus:

- Khoản4 Điều111 trọn vẹn, tách khỏi khoản3 về giá có quy định mới tác động.
- Khoản4 Điều2 NĐ226: định nghĩa nhân khẩu được hỗ trợ, không trộn điều kiện nhóm khác.
- Chỉ gạch thứ5 điểm a khoản2 Điều7 NĐ226, giữ đúng tiêu đề phạm vi NĐ88. **Không mở gạch1/7 đã bị49 bãi bỏ**.
- Đoạn49:16(3g1/g2), giữ câu dẫn hiệu lực và toàn phần bãi bỏ226 để verifier đối chiếu. Trích đoạn bắt đầu ở PDFtrang24, phầng1/g2 ở25–26; link citation là trang bắt đầu, provenance ghi từng phần.

[Provenance theo vị trí/chunk/checksum](provision-provenance-v5.json). Chỉ thêm8liên kết căn cứ theo phạm vi và hoàn thiện ánh xạ bãi bỏ49→226; không sửa raw source/gold/provider/embedding contract hoặc migration.

Các lỗi trực tiếp ngăn ca mục tiêu đã sửa:

- Routing dùng substring “huyen/xa/cu”, nhận nhầm “chuyển/xác/của” thành đổi huyện/xã → nhận diện theo từ.
- Số điều dẫn chiếu trước đó bị gắn nhầm vào văn bản được nêu sau → ưu tiên liên kết điều–số văn bản gần nhau.
- Ngày21/10/2026 bị nhận nhầm là yêu cầu QĐ10/2026 → nhận diện số văn bản có ranh giới, không khớp bên trong ngày.
- Nguồn stale lấn nguồn đã review → ưu tiên receipt đã có trong tập ứng viên, giữ nguyên admission/fail-closed.
- Thiếu liên kết căn cứ quốc gia/sửa đổi, và nhiều đoạn cùng một điều chiếm hết16slot → mở đúng liên kết theo điều nguồn, giữ parent; trong cùng tier review ưu tiên điều khoản khác trước đoạn lặp. Vẫn8primary+8secondary,6requests/12tools/2rounds/1repair/90giây.

Không đổi prompt synthesis, model, verifier OR/AND, guard khoản/đối tượng, F01/finish hoặc thresholds để tạo pass. F03/S06 không được tối ưu/chạy lại.

## 3. Coverage trước/sau và local acceptance

[scope-and-startup-context-pack.json](scope-and-startup-context-pack.json): cùng bộ căn cứ của ba ca, policy Phase2B cấp đủ 0/3 bộ căn cứ hiện hành; policy cuối cấp đủ 3/3. Đây là **source admission**, không phải số đo model trước/sau.

[Acceptance chốt](acceptance-context-pack/report.json) chạy realAgent/retrieval/structural verifier/source gate/citation rendering trênSQLiteriêng. Planner/draft/semantic judge là fixture được ghi rõ. HTTP bị chặn;0Groqrequests/0LLMtokens thực. Input/runtime hashes không đổi trong lượt.

| Nhóm | Số ca | Kết quả |
|---|---:|---|
|Hiện hành C01/C02/C03|3|3answered bằng fixture; retrieval đủ điều đã review, nhưng chỉ1/3 có đủ nội dung căn cứ trong bounded synthesis prompt|
|Thiếu dữ kiện C04|1|clarification_needed, không khẳng định suất|
|Ngoài phạm vi C05|1|insufficient_evidence|
|Căn cứ hiện hành chưa được duyệt C06|1|insufficient_evidence, không phát claim dù fixture cố dẫn nguồn|
|Control lịch sử/đã hỗ trợ S01/S02/S03/N07/N08/N01|6|Đúng trạng thái kỳ vọng; N01 là source-quote fixture, không model benchmark|

Trên **ba ca structural fixture**, tỷ lệ trả lời=3/3 và từ chối=0/3; đây **không phải Answerable Coverage/FAR của pipeline hoặc model**. C01/C03 cần citation tới nguồn không có trong synthesis prompt; C02 có nội dung tương đương trong parent nhưng fixture dùng raw childID. Harness chưa buộc draft fixture chỉ dùng ID/model context được expose. Vì vậy không được gọi3/3 này là acceptance đầy đủ. Không tính các lần từ chối C01 trước đó là đúng: chúng vẫn nằm trong ledger. Không công bố Faithfulness, Citation Accuracy ngữ nghĩa, Answer Correctness hoặc latency model khi chưa chạy/chấm. Integrity chỉ chứng minh ID/text/locator/sourceURL đúng bản, không thay semantic review.

Các lần không đạt được giữ tại `acceptance-1/2/3/4/final/date-fix`; [checkpoint2/3](checkpoint-before-context-pack/) giữ nguyên trước sửa phân bổ context. Hai proposal đầu có scope rộng không hợp lệ với phần226 bị bãi bỏ; chỉ candidatev5 và receipts-final được dùng. `acceptance-1-review.json` ghi lỗi harness/cohort ban đầu. Không loại test, đổi câu hỏi hay expected answer để chọn kết quả đẹp; chỉ hoàn thiện fixture còn thiếu và sửa code/source liên quan.

## 4. Regression và kiểm tra đã chạy

- **461 backend tests PASS** trênPython3.14.4 và3.12.15, cùngrequirements.lock. Có **24 regression cases mới** trong `tests/test_current_legal_candidate.py`: nguyên văn/provenance, biên khoản/bullet bị bãi bỏ, linkPDF/trang, không sửa vector cũ, routing, số điều–văn bản, ngày–số văn bản, receipt ranking, giữ parent/đa dạng điều khoản.
- Frontend 14 tests PASS, productionbuildPASS, Playwright local 100 tests PASS. Không phải publicE2E.
- Secretsscan vàgitdiff--checkPASS.
- Startup với lớp provider thật nhưng transport từ chối mọiHTTP:healthz/readyz/status200,0outbound. Không chứng minh Groq connectivity.
- RestoreSQLite đúng toàn bộdocument; thiếu receipt thì gate khôngusable, nhập lại receipt hợp lệ mớiusable.
- Diagnostic đúng pilot khóaPhase2B: S01/S04/X01/N02 cógold, **Recall@5=1,0,n=4**, E5local/SQLite. Không suy full32, PostgreSQL hoặc model quality. [Kết quả theo từng ca](pilot-retrieval-context-pack.json).

Lần fullsuite đầu có1failure về metadata guides; đã sửa chiều lọc để không loại quan hệ target chưa chứng minh. Logfail giữ nguyên. Chưa chạy Groq/RAGAS/modeljudge/publicchat/PGmigrations hoặc containerbuild trong Phase2C.

## 5. Release candidate identity

| Thành phần | Identity chốt |
|---|---|
|BaseGit|`117e7bd2c4a320c3d02256dfdabf858180b47dbf`; workingtree có patch, chưa commit|
|Candidateidentity|`7a93c43e5098e35f7658888a9e3084147be37c21edec1351c3e380ab9191d0f9`|
|Source-treeSHA256|`ab889c7ff597e6c94f388d794a956a7eac902ee9bf83e21d203a62f8581aedc6`|
|Corpus|`corpus-1afca764aa6692e0`,60docs/7396chunks;4mới|
|PayloadSHA256|`7ce7956ae35c7006b5bfd7d10d516fa9e8e47fe2f073e471ceecbb34b412d317`|
|BackupassetSHA256|`a18c2b8e9563397f752f94479efc5db56091d98d986b7d1e760c1f525a619e49`|
|CanonicalpolicySHA256|`dfe58f8376d4d4d978ace0483ba45a70e60eafa473285ffbe5a6a2a8e7f72dd4`|
|SQLitefingerprint đã kiểm|`ed02cf6e05ab6826bf0270e5af3e2394583c9f97c11c61d8b86aa9faeae7de5a`|
|PostgreSQLfingerprint chỉ dự kiến|`495ed76c2d2e9915b7656d6f16d36b8bff457fd6c31b34cb68e040797c313692`|
|LLM/embedding|Groq`openai/gpt-oss-120b`;`multilingual-e5-small-onnx-q8-window-v1`,384chiều,ONNXQ8, cùngrevision/checksum|

[Manifest đã bổ sung review projection và suite checksums](release-manifest-reviewed.json), [bảo vệ dữ liệu/thay đổi cũ](protection-final.json), [bundle final roundtrip](source-review-bundle-final.json).2341 file có sẵn khác không thay đổi; chỉ 3 file cũ đổi có chủ đích:agent,store,legal_relations. Code/tests có sẵn chưatracked từPhase1/2B cũng được đối chiếu hash. Raw manifest/snapshot/model/golds và mọi artifactPhase1/2B giữ nguyên.

Asset local: `dist/phase2c-current-20261021-context-pack/`, chưa upload/publish. Backup không chứa session/messages/history/answercache; receipts được bundle riêng. CandidateGitSHA đểnull, không giả117e7bd là commit chứa bản vá.

## 6. Quyết định release và bước còn thiếu

**Nguồn được review: đủ3 bộ; structural fixture qua cổng3/3. Synthesis: đầy đủ nội dung căn cứ1/3; pipeline mục tiêu ba nhóm chưa được chứng minh. Deployment: NOT READY.** Còn:

0. Sửa việc chọn nội dung thật sự đưa vào synthesis trong giới hạn hiện có, và bổ sung regression buộc fixture/model chỉ cite nguồn được expose hoặc parent tương đương đúng article. Không nới verifier, tăng token/context cap hoặc chỉnhgold để tạo pass. C01 thiếuNQ254; C03 thiếuND88/ND49. Chưa khuyến nghị chi quota cho pilot3ca trước khi khép blocker này.

1. Pilot model thật một attempt choC01/C02/C03 và semanticreview citations/correctness/faithfulness; không tuyên bố S06pass.
2. PostgreSQLriêng: migrationledger, runtime role,pgvector retrieval,restore receipts và capacity khi giữ cả release cũ/mới. SQLite không chứng minh tương đươngPG.
3. Review changeset, commitSHA đã kiểm thử, pin corpus/policy/runtime. Chưa xác minh deployment hiện phục vụ khớp candidate.
4. Public Turnstile/signedingress/SSE/citation E2E và cloudlatency, sau approval riêng. Không suy từ100mockedbrowsertests.
5. Scope nội dung mới chỉ cho21/10. Nếu vận hành ngày23/10 với câu hỏi mặc định ngày hiện tại phải review thật cho mốc đó; không tự kéo dài checked_at/scope hoặc bật override.

Lệnh commit/push/deploy/rollback cụ thể và thứ tự generationOFF→runtime→corpus→receipts→pin→E2E tại [DEPLOY_ROLLBACK_REVIEWED.md](DEPLOY_ROLLBACK_REVIEWED.md). Rollback về runtime trướcF01 phải giữ generationOFF. Không restore thử/drop production hoặc xóa release cũ trước restore đạt.

## 7. Pilot, demo và giới hạn pháp lý

[PILOT_AND_DEMO.md](PILOT_AND_DEMO.md) chuẩn bị ba câu hỏi, đáp án kỳ vọng, source map và giới hạn cần thể hiện trongUI/báo cáo. Đề xuất pilot3ca, tối đa18generation requests,6/ca gồmretry,90giây/ca,cooldown hiện có; dự toán36–45ktokens, dành45k từ ngân sách generation150k đã đề xuất, không phải ngân sách mới hay hardtoken cap đã triển khai. Chưa được duyệt hoặc sử dụng. Giữ pilot benchmark khóa6ID và tất cảgold; không nhập ba fixture vào score32ca để làm đẹp kết quả.

UI/báo cáo cần nói rõ: chỉVành đai4; đúng mốc ngày/phạm vi review; không toàn bộ chính sách2026; không suy cơ chế đặc thù; không xác định thửa/tính tiền/bảo đảm quyền lợi hoặc suất; hồ sơ thiếu dữ kiện cần bổ sung thông tin đã ẩn danh; ngoài scope phải giới hạn/từ chối. UI chưa được thay trong vòng này.

Dừng Phase2C để người dùng review; không tự chạy pilot, commit, push hoặc deploy.

Không chạy lại hoặc đổi threshold của global release-readiness checker để tạo pass. Các số đo fixture/diagnostic ở đây không chứng nhận global quality gate.

## Điều chỉnh kết luận sau kiểm tra synthesis

[synthesis-projection-review.json](synthesis-projection-review.json) đối chiếu các citation của fixture với `prompt_context` thật sau budget7000 hiện có. C01 thiếu`nq-254-2025-2-0-1`; C03 thiếu`nd-88-2024-0-11-0` và`nd-49-2026-23-scope-16-3g`. C02 đủ nội dung qua`qd-40-2026-hanoi-9-1-parent`. Các outputanswered trước đó không bị sửa/xóa, nhưng được phân loại lại đúng là contract/structural fixture, không model hay pipelinepass. Checkpoint trước review được giữ tại`checkpoint-before-synthesis-review/`. Không sửa code thêm để tối ưu ca trong timebox.
