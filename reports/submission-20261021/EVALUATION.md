# Đánh giá cuối — tách phần mềm, nguồn và đáp án model

Candidate code **`ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec`**, mode `SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`. Bản bàn giao chỉ đọc các đoạn nguyên văn đã review. Không công bố RAG generative đạt nghiệm thu. Mọi cohort lịch sử giữ nguyên; source-only không được kế thừa score retrieval/model như chất lượng đáp án của chính nó.

## 1. Phần mềm và candidate hiện hành

| Kiểm tra | Kết quả có evidence | Phạm vi |
|---|---|---|
| Backend | **529 PASS** | CI Python 3.12; local Python 3.14 là môi trường riêng, không cộng thành 1.058 |
| Frontend unit/build/audit | **16 PASS**, build/audit PASS | Exact code SHA ec5d9a9… |
| Playwright local | **110 PASS**, local full 3,6 phút | Fixtures desktop/mobile; không thay public E2E |
| Image cuối | Build/probe PASS; **381,796875 MiB** dưới 512 MiB | Offline fixture load, không public load test/model inference |
| SQLite source API | PASS, 0 provider calls | Fingerprint `dba69995…` |
| PG16 source API | PASS, 413 SELECT-only queries, không mutate counts, 0 model calls | Runtime role không superuser/bypass RLS; fingerprint `8ee1cd63…` |
| Public deployment/API | Code/corpus/fingerprint đã khớp | Browser public source-only run03 PASS (desktop 1440/mobile emulation 390), 0 model/session |

[CI exact SHA](https://github.com/dovh25x/land-law-chatbot/actions/runs/39588182288), [local backend](../release-final-20261021/backend-full.log), [local Playwright cuối](../release-final-20261021/frontend-e2e-final-full.log), [image probe cuối](../release-final-20261021/image-probe-final.json), [memory cuối](../release-final-20261021/docker-memory-ui-guard.log), [SQLite API](../release-final-20261021/qa/source-lookup-acceptance.json), [PG API](../release-final-20261021/qa/source-lookup-pg-acceptance.json), [public identity](../release-final-20261021/final-public-identity.json).

Baseline Phase 3B/4 có 516 backend và 100 local UI tests; candidate nguồn đầu có 104 UI. Các số này là các phiên bản suite, không cộng vào 529/110. Số 13 backend mới giải thích 516→529; 56 targeted đã bao gồm 13 mới, không cộng 56+13. Các run partial/FAIL giữ trong evidence index.

## 2. Retrieval Recall@5 — cohort RAG riêng

[Receipt gốc](../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json): SQLite cách ly, corpus `corpus-1afca764aa6692e0`, fingerprint đầy đủ `1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d`. Dùng query gốc/E5/hybrid search và replacement candidates hiện có; không rewrite, model generation, judge hoặc agent tool expansion.

Với gold chunks `G_i` và top-five IDs `R_i^5`:

- `Recall@5_i = |G_i ∩ R_i^5| / |G_i|`.
- `Macro Recall@5 = Σ_i Recall@5_i / n`.
- `Micro Recall@5 = Σ_i |G_i ∩ R_i^5| / Σ_i |G_i|`.

| Mẫu số | Kết quả |
|---|---:|
| Queries có positive gold hợp lệ | 19: 10 smoke, 3 supplemental, 6 natural |
| Macro | `(18×1 + 0,5)/19 = 97,37%` |
| Gold chunks hit / labels | 20/21 |
| Micro | `20/21 = 95,24%` |
| Natural split | 6 câu; macro 91,67% |

S06 loại trước run theo chỉ dẫn không chạy lại; 12 ca không có positive gold không có mẫu số Recall. Tổng suite khóa 20+4+8 không đổi. N03 thiếu gold parent dù child liên quan có mặt; không coi ID tương đương để tăng score. Diagnostic review admission trên chính top-five gốc không refill cũng có macro 97,37%, nhưng không chứng minh toàn corpus fresh. Ngày hỏi theo từng case, có cả historical; không phải kiểm current-law coverage cho mọi ngày.

**97,37% là retrieval Recall@5, không phải legal-answer accuracy, Citation Accuracy hoặc score của mode nguồn cuối.** PostgreSQL Recall@5 chưa đo; không chuyển kết quả SQLite sang PG.

## 3. Context và citation integrity

- [Actual synthesis capture](../phase3b-reliability-20261021T073924Z/synthesis-final/report.json) giữ C02 3/3 required units, 5.070 ký tự; C03 7/7, 6.981/7.000 ký tự. Đây là completeness, không phải model-answer pass.
- [C02 actual-wire QA](../release-final-20261021/qa/c02-pilot-review.md) xác nhận đúng câu hỏi khóa, không gold/history, 3/3 required units; cả 5 synthesis passages fresh đúng checksum/ngày. Payload khớp synthesis snapshot; không có nguồn ngoài snapshot dùng để cite.
- Source-quote fixture Phase 3B phát hành một claim/một citation, nhưng generation và semantic judge đều là fixture. Coverage fixture 9/11 ở fingerprint `8051…` giữ hai FAIL; không biến thành model score hoặc chuyển sang fingerprint `1697…`.
- Mode nguồn cuối chỉ hiển thị đúng passage được review; locator/URL/checksum giúp kiểm provenance. **Integrity không tự chứng minh citation hỗ trợ đầy đủ một kết luận tổng hợp.** Không có model answer thì không gán semantic Citation Accuracy bằng 100%.

## 4. Model outcomes và API reliability

| Cohort/case | Outcome giữ nguyên | Requests/usage/latency | Điều chưa đo |
|---|---|---|---|
| S06 cuối, fingerprint `2dab…` | **FAIL** | 2 HTTP200; 8.104 confirmed tokens; 5.815 ms | Không có published claim; không đổi repair cải thiện thành PASS |
| C01 Phase 3A, `37d2…` | **INCOMPLETE** | 3 HTTP requests; 4.829 confirmed; 34.858 ms | Draft đầu không đủ phát hành; 429 TPM, 400 JSON, budget stop |
| C02/C03 Phase 3A | **NOT RUN** | 0 attempts/0 requests | Placeholder INCOMPLETE trong raw execution không phải inference đã bắt đầu |
| C02 mới, `1697…`, allocation độc lập | **INCOMPLETE** | 1 HTTP400; 6.951 ms whole-turn, 5.252 ms wire | Không Draft hợp lệ, không semantic verifier verdict hoặc published answer/citation |

[S06](../phase1-s06-final-20261020T161058Z-b031ce/technical-review.json), [Phase 3A](../phase3a-live-20261021T070325Z/execution.json), [C02 mới](../release-final-20261021/pilot-C02/attempt.json), [response C02](../release-final-20261021/pilot-C02/wire/01/response.json).

S06 vẫn FAIL dù repair cải thiện scope/OR; structural guard chưa chấp thuận, không đủ căn cứ tuyên bố PASS. C01 có issue citation/điều kiện và lỗi thực thi; không gọi mọi issue lexical là kết luận pháp lý độc lập. C02 mới provider báo `json_validate_failed` vì output bị truncate tại max completion 2.048 và thiếu properties bắt buộc; không quy cho app parser hoặc suy nội dung pháp luật của failed_generation chưa lưu. Không có 429 trong C02 mới. Không rerun/tune C01/S06/C02 hoặc chạy judge ngoài pipeline.

### Token accounting — không cộng hai allocations

| Allocation | Confirmed | Unknown upper bound | Reserved cuối | Remaining |
|---|---:|---:|---:|---:|
| Phase 3A 60.000 | 4.829 | 47.330 | 0 | 7.841 |
| C02 độc lập 25.000 | 0 được xác nhận | 19.788 | 0 | 5.212 |

[Ledger gốc](../phase3b-reliability-20261021T073924Z/prior-allocation-ledger.json), [ledger C02 mới](../release-final-20261021/pilot-C02/request-budget.json). `confirmed_usage=0` không nghĩa actual usage bằng 0. Upper bound/reservation không phải token provider đã đo; unknown không được tự refund. Request C02 tiếp theo bị chặn trước network, không vượt cap. Internal budget khác quota provider; không suy RPM/TPD exhaustion chỉ từ các headers thiếu định nghĩa trong run.

## 5. Public browser, safety và latency

Run public đầu **FAIL** do harness đợi URL ngày dư thừa dù default-day GET hợp lệ; [sidecar](../release-final-20261021/qa/public-source-run-01-harness-review.json) giữ nguyên failure và sửa kỳ vọng, không tăng timeout hoặc đổi scope luật. Run public thứ hai **FAIL thật** do history/citation cũ xuất hiện trước metadata source-only. [Diagnostic](../release-final-20261021/qa/history-race-2026-10-21T10-37-55-451Z/report.json) ghi 528 ms thấy old citation và 20,767 giây mode metadata về. Đây là seeded synthetic history trong browser riêng, không phải một output model mới.

[Guard trình bày](../release-final-20261021/qa/UI_UNKNOWN_RUNTIME_FIX.md) fail-closed khi metadata pending/failed và không dùng focus để mở lại panel chưa tin cậy. Candidate trung gian 93d có [CI FAIL](https://github.com/dovh25x/land-law-chatbot/actions/runs/39586847824) trước deploy; không gán CANCELLED vì yêu cầu hủy đến sau khi run kết thúc. Code ec5 hoàn chỉnh có CI PASS. [Full public source-only browser run03](../release-final-20261021/qa/public-source-2026-10-21T11-02-32-079Z/report.json) đã PASS trên đúng final code ec5/corpus/fingerprint,1440px desktop/390px emulated mobile. Checksum/date43/1/25, link chính thức HTTP200 đúng title, source panel, reload/immediate history warning/clear và không overflow đạt, 0 model/session. Không physical-device test hoặc full generative E2E. Hai FAIL gốc không bị xóa hay thay bằng local fixtures.

Latency model hiện có chỉ là các incomplete attempts n=1/case trong bảng trên, không phải successful-answer latency hoặc p95. Public source/status latency của run lỗi là network/API observations, không gọi model latency. Chưa có load test hoặc phân phối latency public đủ mẫu; không tự tính p95 ổn định. Human Turnstile, generative chat và follow-up không được kiểm/thực hiện trong source-only mode; không gọi full generative E2E PASS.

## 6. Metrics chưa đo

| Metric | Trạng thái | Yêu cầu để đo đúng |
|---|---|---|
| RAG model Answer Correctness | **NOT MEASURED** như aggregate cuối | Proposition/rubric khóa, reviewer, report completed/incomplete và mẫu số |
| Semantic Citation Accuracy | **NOT MEASURED** | Chấm từng claim–citation, đúng subject/ngày/ngoại lệ; khác integrity |
| RAGAS Faithfulness | **NOT MEASURED** | Chạy RAGAS thật, version/judge/input được ghim và budget được duyệt |
| Custom faithfulness final | **NOT MEASURED** | Evaluator riêng, không đổi tên thành RAGAS |
| Answerable Coverage / False Abstention Rate | **NOT MEASURED** | Sidecar answerability được review/khóa trước run; incomplete riêng, refusal ca answerable không tự đúng |
| Model/public p50/p95 | **NOT MEASURED** trên bộ đủ mẫu | Tách cold start, network, source GET, whole-turn và model time |
| PostgreSQL Recall@5 | **NOT MEASURED** | Dataset/ngày/gold/backend cohort riêng |

Mode nguồn không có generated legal answer để chấm các metrics tổng hợp đó; không dùng zero claims làm faithfulness=1. Historical [custom sampled faithfulness `c4f0…`](../evaluation/ring4-c4f0c661/faithfulness.json) có 12/13 supported claims (0,9231), 6/8 sampled cases; [cohort `800c…`](../evaluation/ring4-800c96ba/faithfulness.json) không có case scored, score null. Không phải RAGAS, không independent legal certification, không gộp hoặc dùng null thành zero/one.

## 7. Source scope và tái lập

Actual API source-only có 25 passages cho 02/08/2024, 43 cho 21/10/2026, ngày 22–23 chỉ1 header QĐ 40. Không suy current coverage ngày 23 từ ngày 21. Archived receipt chỉ chứng nhận scope/time đã review; live import yêu cầu review gần đây không quá 7 ngày. Restore có thể khớp bytes nhưng activation sau expiry cần renewed review hợp lệ; không đổi `checked_at`, gia hạn hàng loạt hoặc bypass F01.

Các giới hạn thực nghiệm: mẫu nhỏ/tác giả chọn, cùng người viết code/gán nhãn, nhiều vòng chỉnh trên cùng tập, thiếu holdout/người review độc lập, khác SQLite/PG và judge cùng model ở các run lịch sử. [LIMITATIONS](LIMITATIONS.md) nêu rõ; [delivery status](delivery-status.json) và evidence index giữ identity/outcomes hiện hành. Thay phần mềm/nguồn hoặc thu hẹp mode không biến các model failures thành PASS.
