# Tổng hợp đánh giá cuối kỳ

Chốt evidence ngày 21/10/2026. Đây là tổng hợp các lần chạy đã lưu, không phải một benchmark mới. Phase 4 không gọi Groq hoặc judge, không chạy lại S06/C01, không sửa gold và không cấp lại ngân sách. Danh tính đầy đủ ở [freeze manifest](freeze-manifest.json); vị trí và checksum evidence ở [index](EVIDENCE_INDEX.md).

## 1. Các cohort phải đọc riêng

| Cohort | Runtime fingerprint (rút gọn) | Kết luận được phép |
|---|---|---|
| S06 cuối, 20/10 | `2dab4dde6932…` | S06 FAIL; corpus cũ `corpus-a26bc99e541fbbe2` |
| Phase 2D và Phase 3A | `37d2fb54ca0c…` | Context capture; C01 INCOMPLETE; C02/C03 NOT RUN trong pilot |
| Phase 3B fixture trung gian | `80512d4e04f0…` | 9/11 fixture status matches; C02/C03 fixture FAIL |
| Phase 3B runtime cuối | `1697d9dec78b…` | Software/retrieval/context/quote fixture; không có model inference |
| PostgreSQL Phase 4 local | `2229a1b29805…` | Migration/role/restore đạt trên PG cách ly; Phase 3B mới là planned-only; không suy SQLite = PG |
| Faithfulness lịch sử | `c4f0c661af82…`, `800c96bad3ff…` | Báo riêng evaluator tùy biến; không gán cho candidate cuối |

Thay đổi Phase 4 chỉ gồm tài liệu, công cụ kiểm chứng evidence và packaging; không có bản vá sinh/kiểm chứng đáp án. Các kiểm tra Docker được người dùng cho phép bổ sung ghi riêng ở [release checklist](RELEASE_CHECKLIST.md), không biến thành model evaluation.

## 2. Software tests

| Kiểm tra | Evidence Phase 3B | Kết quả và giới hạn |
|---|---|---|
| Backend | `backend-tests-final-2.log` | 516 passed, 33,70 s; Python 3.14.4; chặn HTTP model thật |
| Budget/provider regression | `accounting-tests-after-import-check.log` | 30 passed; là tập con, không cộng thành 546 tests |
| Frontend unit | `frontend-tests.log` | 14 passed |
| Frontend build | `frontend-build.log` | PASS, không xác nhận public website |
| Playwright | `frontend-e2e.log` | 100 passed; API fixture trên local, không có Groq/Turnstile production |
| Secret scan | `secrets-check-final.log` | PASS tại thời điểm Phase 3B; Phase 4 có scan cuối riêng |

Bổ sung Phase 4 theo chấp thuận Docker: serving image build đạt, image probe Python 3.12.15/model hashes/fingerprints/non-root đạt; memory check 382,66 MiB/512 MiB đạt. Lần pytest trong serving image thiếu Git/notebook:513 pass/3 fail (giữ log); testtools layer chỉ thêm Git và mount notebook sau đó đạt **516 passed trong 64,43 s**, network-none/chặn HTTP. Không cộng thành nhiều hơn 516 test độc lập hoặc gọi serving image đã đủ công cụ dev. PostgreSQL 16.15/pgvector 0.8.7 container cách ly đạt migrations 001–006, runtime role, leases và round-trip corpus 60/7396; không phải full suite trên PG, RecallPG hoặc cloud. [Docker receipt](docker-preflight.json), [PG receipt](postgres-preflight.json).

Tái sử dụng kết quả chỉ khi checksum source tương ứng còn khớp; thay đổi `.dockerignore` phải kiểm tra đóng gói riêng. Python 3.12/image/PG không được suy từ Python 3.14. Chi tiết preflight bổ sung và exit codes nằm trong manifest/checklist, không được gọi là CI đã chạy.

## 3. Retrieval Recall@5

Nguồn: [receipt và từng hàng](../../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json). Backend: **SQLite cách ly**, runtime `1697d9dec78b…`, corpus `corpus-1afca764aa6692e0`. Không có LLM calls.

Với câu i, `G_i` là tập gold chunk IDs đã khóa và `R_i^5` là năm ID truy xuất đầu tiên:

`Recall@5_i = |G_i ∩ R_i^5| / |G_i|`.

`Macro Recall@5 = (Σ_i Recall@5_i) / N = (18 × 1 + 0,5) / 19 = 97,3684% ≈ 97,37%`.

`Micro Recall@5 = Σ_i |G_i ∩ R_i^5| / Σ_i |G_i| = 20 / 21 = 95,2381% ≈ 95,24%`.

| Split khóa | Câu được tính | Macro Recall@5 |
|---|---:|---:|
| Smoke (tập 20) | 10 | 100% |
| Supplemental (tập 4) | 3 | 100% |
| Natural (tập 8) | 6 | 91,67% |
| Tổng | 19 | 97,37% |

32 câu của bộ 20+4+8 được giữ nguyên. S06 loại **trước chạy** theo yêu cầu không chạy lại; 12 câu không có positive gold chunks loại khỏi mẫu số Recall. Receipt ghi đủ 13 trường hợp loại và lý do. Đây không phải score của cả 32 câu hay test set ngẫu nhiên đại diện người dân. Ngày hỏi của mỗi câu giữ nguyên, gồm cả lịch sử; không gọi toàn bộ là câu hiện hành 21/10/2026.

N03 chỉ trúng một trong hai gold IDs: parent `luat-dat-dai-2024-107-1-parent` không có trong top 5 dù child liên quan có mặt. Không đổi gold hoặc đồng nhất parent/child sau khi xem kết quả. Diagnostic admission dùng chính top 5 này, không refill, cũng đạt macro 97,37%; không chứng minh toàn corpus đã fresh. Metric dùng query gốc với candidate search/replacement handling, không cộng kết quả sau agent tool expansion. Chưa đo Recall@5 trên PostgreSQL/pgvector hoặc public candidate trong cohort này.

## 4. Context completeness và citation integrity

| Kiểm tra | Evidence | Kết quả |
|---|---|---|
| Phase 2D C01/C02/C03 | [locked capture](../../phase2d-synthesis-20261021/acceptance-locked/report.json), FP `37d2…` | 4/4, 3/3, 7/7 required units; không inference |
| Final C02 | [capture](../../phase3b-reliability-20261021T073924Z/synthesis-final/report.json), FP `1697…` | 3/3, 5.070 ký tự serialized evidence/documents |
| Final C03 | Cùng receipt | 7/7, 6.981 ký tự; sát giới hạn 7.000 |
| Final quote fixture | [startup/quote receipt](../../phase3b-reliability-20261021T073924Z/startup-and-positive-fixture-final.json) | Một claim/một citation đã review, thuộc synthesis snapshot; semantic judge là fixture |
| Coverage fixture trung gian | [11-case receipt](../../phase3b-reliability-20261021T073924Z/coverage-preflight/report.json), FP `8051…` | 9/11 status matches; C02/C03 FAIL do cite child ngoài snapshot thực chọn parent |

Final capture dùng provider ghi payload rồi trả Draft từ chối có chủ ý; không chấm những refusal đó là model false abstention. Trường cũ `all_three_complete=false` trong receipt final không đại diện C01/C02/C03: lần chạy đã lọc hai ca dương và các ca âm; đọc các bản ghi từng case. Không sửa artifact lịch sử để đổi ý nghĩa trường này.

Citation integrity kiểm tra provenance/ID/locator/excerpt/checksum, khác **Citation Accuracy** là citation có thực sự chứng minh toàn bộ claim, chủ thể, ngoại lệ và ngày áp dụng hay không. Không có published citations thì metric accuracy/faithfulness không tự bằng 100%.

## 5. Kết quả model thật và API

| Case | Cohort | Attempts/HTTP | Kết quả công bố |
|---|---|---:|---|
| S06 | Lần cuối Phase 1 | 1 / 2 | **FAIL**; refusal, không published claim/citation |
| C01 | Phase 3A | 1 / 3 | **INCOMPLETE**; draft correctness issue, 429, JSON validation, budget stop |
| C02 | Phase 3A | 0 / 0 | **NOT RUN** |
| C03 | Phase 3A | 0 / 0 | **NOT RUN** |
| C01/C02/C03 | Runtime cuối Phase 3B/4 | 0 / 0 | **NOT RUN**; không có model answer pass mới |

Raw `execution.json` Phase 3A dùng placeholder `INCOMPLETE` cho C02/C03 nhưng `attempt_started=false`. Summary này chuẩn hóa thành NOT RUN theo yêu cầu, bảo toàn raw receipt và giải thích sự khác biệt. Không đổi attempt count vì repair/retry.

**C01:** HTTP 200 đầu sinh Draft có lỗi nội dung/citation, verifier không chấp nhận. Synthesis có đủ 4/4 required units, 6.697 ký tự; do vậy “không tìm thấy nguồn” không giải thích đầy đủ lỗi đáp án. Một issue của structural verifier nhạy cách diễn đạt; chỉ dùng cả trace để kết luận draft chưa đủ phát hành, không kết luận mọi phần đều sai. Sau đó HTTP 429 và HTTP 400 khiến repair không hoàn tất; không có đáp án hợp lệ để tính accuracy.

| Sự kiện xác nhận | Giá trị từ wire receipts | Phần chưa biết |
|---|---|---|
| HTTP 200 | 3.474 prompt + 1.355 completion = 4.829 tokens; 3.756 ms | Không có model pass dù 200 |
| HTTP 429 | Body: TPM limit 8.000, used 4.254, requested 4.198; `retry-after=4`; token remaining 3.746, reset 31,904 s; 148 ms | Không chứng minh vượt RPM/RPD/TPD; request headers có semantics riêng |
| Cooldown | Khoảng từ 429 đến retry ít nhất 4,497 s | Không bằng chứng double-retry trong ba wire calls |
| HTTP 400 | `json_validate_failed`, `invalid_request_error`, 4.941 ms | Không lưu failed_generation; không thể dựng lại JSON sai hoặc quy toàn bộ cho parser |
| Turn | 34.858 ms, 0 published claims/citations | Không phải latency đáp án thành công hoặc public p95 |

S06 giữ FAIL: repair cải thiện phân biệt chủ thể và OR nhưng structural guard vẫn chặn, chưa có semantic verification chấp thuận. Không coi việc sửa fixture hoặc lập luận hậu kiểm là biến ca này thành PASS.

## 6. Token accounting và ngân sách còn lại

Confirmed usage **4.829** là số provider xác nhận. Hai request không có usage giữ unknown upper bounds tổng **47.330**; `reserved_budget=0` khi không có request in-flight. Tổng accounting 52.159 không phải tokens thực đo. `remaining_test_budget=60.000−4.829−47.330=7.841`.

Phase 3B bảo toàn allocation gốc bằng [ledger](../../phase3b-reliability-20261021T073924Z/prior-allocation-ledger.json). Reservation C02 ban đầu trên runtime mới là **19.788**, lớn hơn 7.841; [dry precheck](../../phase3b-reliability-20261021T073924Z/prior-allocation-check.json) chặn trước HTTP, **0 external requests**. Không reset ngân sách bằng thư mục output mới. Usage không biết không được tự refund. Budget nội bộ khác provider quota: có budget cũng có thể bị TPM/RPD chặn, và quota provider còn chưa cho phép vượt hard cap nội bộ.

Runtime mới tách confirmed/estimated/reserved/remaining và dùng giới hạn bảo thủ theo body bytes + framing allowance + max output. Chưa có chứng minh tokenizer/framing nhỏ hơn để giải phóng các khoản unknown. Phase 4 không thay hard cap hoặc tự phê duyệt allocation mới.

## 7. Metrics chưa đo và protocol còn thiếu

| Metric | Trạng thái final runtime | Phương pháp cần làm sau phê duyệt |
|---|---|---|
| Model Answer Correctness | **NOT MEASURED** | Review từng proposition/ngoại lệ theo rubric và case khóa; báo PASS/PARTIAL/FAIL/INCOMPLETE và mẫu số attempts/completed |
| Citation Accuracy | **NOT MEASURED** | Chấm từng cặp claim–citation theo nội dung, subject, ngày, ngoại lệ; tách integrity khỏi support |
| RAGAS Faithfulness | **NOT MEASURED** | Chạy RAGAS thật, ghim package/judge/version và inputs, nếu được duyệt; không tự đổi tên evaluator hiện có |
| Custom faithfulness final | **NOT MEASURED** | Evaluator hiện có, báo raw support counts/unscored; cần judge approval và budget |
| Answerable Coverage | **NOT MEASURED** | Khóa sidecar answerability trước run; số case answerable có câu trả lời / tất cả case answerable; báo thêm tỷ lệ đúng |
| False Abstention Rate | **NOT MEASURED** | Số refusal sai / tổng case answerable; INCOMPLETE báo riêng, không loại âm thầm |
| Safety rate model | **NOT MEASURED** | Các câu thiếu dữ kiện/ngoài scope có đúng nhánh, không phát legal claim sai; không thay bằng unit pass |
| Latency final/public p50/p95 | **NOT MEASURED** | Ghi whole-turn/request/cooldown/cold start và completed/incomplete; mẫu nhỏ không diễn giải p95 ổn định |
| Recall@5 PostgreSQL | **NOT MEASURED** trong cohort retrieval 19 câu | Giữ nguyên IDs/query/ngày/gold, chạy trên PG cách ly và báo cohort riêng |

Answerable Coverage ở đây đo **có trả lời**, không tự đo đúng. Có thể thêm Correct Answer Coverage = số đáp án đúng / tất cả case answerable nếu được khóa protocol. Không chấm refusal là đúng cho ca đủ căn cứ; safety refusal đúng ở ca ngoài phạm vi phải có nhãn riêng.

Historical custom faithfulness: [cohort c4f0…](../../evaluation/ring4-c4f0c661/faithfulness.json) có 12/13 claims supported = 0,9231 trên 6/8 sampled cases; [cohort 800c…](../../evaluation/ring4-800c96ba/faithfulness.json) 0/8 scored, giá trị null. Không phải RAGAS, không phải final runtime, không gộp, không dùng null thành zero hoặc one. Các kết quả lịch sử khác giữ nguyên và được tra qua index.

## 8. Kết luận đánh giá

Có evidence cho software, retrieval SQLite và context/provenance. Chưa có evidence model answer success trên runtime cuối, chưa có quality aggregate hoặc public E2E hợp lệ. **Deployment NOT READY** và **pilot với allocation cũ NOT READY**. Không yêu cầu tối ưu thêm S06/C01. Nếu được duyệt một bước tiếp theo, ưu tiên xác minh PG/image/public configuration và giải quyết điều kiện ngân sách minh bạch trước khi đề nghị duy nhất một C02 pilot có đủ nguồn; không tự thực hiện.
