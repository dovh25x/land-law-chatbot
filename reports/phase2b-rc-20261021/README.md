# Phase 2B — Legal Source Gate & Release Candidate Preparation

**Kết luận: NOT READY cho bước deploy.** Đã chuẩn bị candidate local có cổng nguồn theo điều khoản/thời điểm, receipts có checksum, kiểm thử và bộ asset. Phạm vi nội dung hiện hành còn hẹp; PostgreSQL, model pilot và public E2E chưa được xác minh. Không dùng fixture pass hay source coverage để tuyên bố model đạt.

Ngày thực hiện: **21/10/2026, giờ Việt Nam**; timestamps bằng chứng giữ UTC. Bắt đầu lúc `2026-10-20T17:00:32Z`, trong timebox tối đa 90 phút. Không gọi Groq/judge, không chỉnh production DB, credentials, corpus/vector/model, không commit/push/deploy. S06 giữ FAIL, không tối ưu thêm F03.

## 1. Nguồn đã xác minh và phạm vi MVP

Sáu nguồn có **38 đoạn được duyệt theo scope và ngày hỏi**. Không nguồn nào được gắn fresh toàn văn chỉ vì HTTP/hash. Toàn corpus vẫn **59 stale +1 unknown**, nhưng các đoạn đúng scope có thể được dùng qua receipt đã ghim.

| Nguồn | Phần được duyệt | Khoảng ngày hỏi `[from,to)` |
|---|---|---|
| Luật 31/2024/QH15 | Điều 91, 95, 104, 108, 109; giữ chủ thể/điều kiện và parent context | 01/08/2024–01/01/2025 |
| Luật 43/2024/QH15 | Điều 1 và 5; thay mốc hiệu lực của Luật 31, không sửa các điều trên | 01/08/2024–01/01/2025 |
| NĐ 88/2024/NĐ-CP | Điều 19, 30, 31; phân biệt khoản 1/2 Điều 31 | 01/08/2024–01/07/2025 |
| NĐ 151/2025/NĐ-CP | Điều 5, 21; điểm d khoản 1 Điều 5 chuyển cho **Chủ tịch UBND cấp xã** | 01/07/2025–15/08/2025 |
| QĐ 10/2026/QĐ-UBND Hà Nội | Điều 2, 3 của Quyết định; không bãi bỏ toàn QĐ 38 | 18/01/2026–02/04/2026 |
| QĐ 40/2026/QĐ-UBND Hà Nội | **Chỉ Điều 2 của Quyết định**, ngày hiệu lực và thay thế; không phải Điều 2 của Quy định kèm theo | 01/01/2026–28/10/2026; chỉ facts này, còn chịu hạn review 7 ngày |
| QĐ 56/2024 Hà Nội | GET chính thức trả 403; không duyệt từ nguồn gốc | unknown, receipt unavailable |
| 53 nguồn khác | Chưa review đủ phạm vi/quan hệ để phát claim mới | stale |

Mapping đủ 32 ca có văn bản, điều/khoản, ngày hỏi và trạng thái tại [SCOPE_MAPPING.md](SCOPE_MAPPING.md), bản máy đọc ở [scope-mapping.json](scope-mapping.json). Cả 20 ca có gold chunk đều có source scope phù hợp tại ngày hỏi; đây **không phải 20 ca trả lời đúng**. S06 có đủ nguồn vẫn giữ lỗi model/verifier đã biết.

Nguồn, phần đã đọc, quan hệ sửa đổi/thay thế/chuyển tiếp và giới hạn ở [SOURCE_REVIEW.md](SOURCE_REVIEW.md). Evidence GET/PDF hashes ở [source-access.json](source-access.json), [source-access-supplement.json](source-access-supplement.json); receipts ở [receipts](receipts/), policy cuối ở [source-gate.json](source-gate.json).

**Giới hạn đáng kể:** đa số câu hỏi nội dung trong bộ khóa hỏi ngày 02/08/2024. Với câu hỏi không ghi ngày, mặc định hiện tại, policy chỉ mở facts hiệu lực/thay thế của QĐ 40; câu hỏi nội dung bồi thường/hỗ trợ/tái định cư hiện hành nhìn chung vẫn bị hạn chế hoặc từ chối. Muốn phục vụ người dân theo pháp luật hiện hành cần khép review NQ 254/NĐ 49/NĐ 226, phần Quy định kèm QĐ 40 và các chính sách/quan hệ Luật Thủ đô có liên quan. Không giải quyết gap bằng snapshot override hoặc tự gắn fresh toàn corpus.

## 2. Thay đổi và regression

Xem đủ 18 paths thay đổi trong vòng này tại [CHANGESET.md](CHANGESET.md). Các thay đổi chính:

- Strict source policy dùng `app_state` và `source_reviews` hiện có, ghim receipt checksum, chunk checksum và khoảng ngày hỏi. Chỉ review một số đoạn không làm fresh toàn văn.
- Từng claim được kiểm trước verifier và kiểm lại ở finish. Snapshot override/ngày lịch sử không vượt strict gate; changed, unavailable, sai đoạn/ngày, receipt hết hạn hoặc chưa ghim đều chặn.
- Bỏ kiểm tra all-fresh toàn corpus **chỉ khi có strict policy**; API/ops-status phản ánh khả dụng theo scope. Nếu không có đoạn hợp lệ, từ chối trước synthesis và nêu rõ thiếu phạm vi.
- Backup giữ policy, restore thiếu receipt vẫn fail-closed. Importer chỉ chấp nhận CDN Công báo khi đúng attachment đã ghim và gắn nguồn công bố chính thức.
- Helper evaluation nhập receipts và khóa source cohort; không trộn artifact chỉ vì cùng model/corpus. Ignore backup corpus local trong Git/Docker image.
- Hai fixture danh bạ sửa ngày UTC thành ngày Việt Nam; không sửa runtime để nới guard. Không chỉnh prompt/clause dependency/OR-AND F03.

| Kiểm tra thực tế | Kết quả | Bằng chứng |
|---|---|---|
| Backend Python 3.14 | **437 passed** | [log](backend-tests-rc-final.log) |
| Backend Python 3.12, cùng lockfile | **437 passed** | [log](python312-backend-tests-rc-final.log) |
| Frontend unit | **14 passed** | [log](frontend-tests.log) |
| Frontend production build | **Pass** | [log](frontend-build.log) |
| Playwright local | **100 passed** | [log](frontend-e2e.log) |
| Secret scanner | **Pass** | [log](secrets-check.log) |
| FastAPI startup, real provider class với outbound transport bị chặn | health/ready/status **200**, 0 outbound | [report](backend-startup.json) |

34 regression cases mới gồm scope/date/checksum, snapshot true/false, adverse/expired/replaced receipt, malformed policy, restore thiếu receipt, status/startup, CDN đúng/sai attachment và evaluation cohort lock. Các lỗi ban đầu và lỗi harness/import được giữ trong logs, không bỏ để tạo lịch sử chỉ có pass.

[check-exit-codes.json](check-exit-codes.json) ghi exit code thực. [protected-input-verification.json](protected-input-verification.json) xác nhận 117 file evidence/suite/F01/F03 trước vòng không đổi. [corpus-and-model-protection.json](corpus-and-model-protection.json) xác nhận 17 input về corpus, evaluation và model/config giữ hash của preflight.

## 3. Trả lời/từ chối trên SQLite riêng

[Replay policy cuối](final-policy-replay/report.json) ghi contexts, draft, verifier, output/citations, fingerprint và usage. Inputs được so hash trước/sau, không đổi trong replay. Không có HTTP Groq client; E5 chỉ embed query local.

| Ca | Kết quả | Ý nghĩa |
|---|---|---|
| S01 | answered, 1 citation, 0 LLM | Fact thay thế QĐ 56 từ đúng QĐ 40 |
| S02 | clarification_needed, 1 citation, 0 LLM | Nêu đúng mốc hiệu lực tương lai đối với ngày hỏi; không tính quyền lợi |
| S03 | answered, 1 citation, 0 LLM | Bãi bỏ Điều 2 QĐ 38, không bãi bỏ toàn văn |
| N07 | clarification_needed, 0 citation, 0 LLM | Không bảo đảm suất tái định cư từ thông tin thiếu |
| N08 | insufficient_evidence, 0 citation, 0 LLM | Không xác nhận nội dung văn bản chưa có nguồn |
| UNREVIEWED-CURRENT | insufficient_evidence, 0 citation, 0 LLM | Điều 104 tại ngày hiện tại chưa được scope duyệt |
| N01 synthesis fixture | answered, 1 citation, 2 fixture calls, **0 HTTP** | Chỉ kiểm plumbing source gate/verifier, **không phải model evaluation** |

Control dương hỏi **ngày hiện tại** ở [current-source-gate-check.json](current-source-gate-check.json): answered, 1 citation, 0 LLM trong khi whole-corpus freshness=false. Đây là tình huống demo ngoài suite, không phải benchmark mới. Nó chứng minh global freshness không chặn mọi câu hỏi có nguồn đủ, nhưng không chứng minh coverage nội dung hiện hành đã đủ.

[Citation integrity](citation-integrity-checks.json) kiểm excerpt/locator/URL/số văn bản/page/attachment checksum và phạm vi; có một fixture được ghi nhãn. Đây chưa phải semantic Citation Accuracy. Citation `checked_at` vẫn là provenance snapshot gốc; ngày review mới nằm trong receipt, không sửa snapshot để đổi timestamp.

Restore SQLite giữ nguyên documents/chunks/vectors; có policy nhưng thiếu receipt thì unusable, nhập lại receipt hợp lệ thì usable. Helper thật cũng đã chạy nhóm S01/N07/N08 với `--no-generation`, lưu source-policy lock và 0 LLM trong [helper-offline-guards-final](helper-offline-guards-final/). Không gộp các lượt dùng policy ban đầu vào cohort cuối.

## 4. Release manifest và điều kiện thiếu

[release-manifest.json](release-manifest.json) và [RC-SHA256SUMS](RC-SHA256SUMS) bind code/tree, corpus asset, receipts, suite, scorer, presentation và model/embedding identity.

- Base HEAD: `117e7bd2c4a320c3d02256dfdabf858180b47dbf`; **candidate commit SHA chưa có**, vì chưa commit theo yêu cầu. Không dùng base SHA như thể đã chứa patch.
- Runtime SQLite đã kiểm: `8d4e3ce8a31e5b6dc7e960ffbcd970a199499e12bd7a18a62affdff68378fe79`.
- Runtime PostgreSQL **dự kiến, chưa chạy**: `932e279a731beef773beaa75b0f20395c270a7c59f4c56acbd64ae5ac68fd0e7`.
- Canonical source policy: `e4ce2a3b06e97b76af3d779013d8e238dac07fa4c1b0c8c0ef181dae436edff3`.
- Corpus giữ `corpus-a26bc99e541fbbe2`, 60 tài liệu/7.392 chunks; Groq GPT-OSS 120B, E5 ONNX Q8 384 chiều và hai lockfiles giữ nguyên.
- Asset corpus và source-review ZIP cuối đã đóng gói local tại `dist/phase2b-rc-20261021/`, chưa publish. Corpus asset khớp bytes đã restore SQLite; ZIP được roundtrip checksum.

Chưa kiểm: PostgreSQL migration/role/restore/retrieval; Docker image; real model/judge pilot trên identity cuối; tải asset từ Release rồi restore; public chat E2E; rollback control plane. Không sửa quality thresholds để biến các phần thiếu thành pass.

## 5. Deploy/rollback

Quy trình và lệnh cụ thể ở [DEPLOY_ROLLBACK.md](DEPLOY_ROLLBACK.md), paths đề xuất stage ở [reviewed-paths.txt](reviewed-paths.txt). Cần user review trước commit/push/deploy.

Điểm bắt buộc: tắt public generation trước khi import receipts vào runtime cũ; giữ model/embedding/secrets/Free hosting; corpus đang khớp nên không restore lại serving corpus; kiểm đúng SHA + PostgreSQL fingerprint + policy hash sau rollout. Rollback về runtime trước F01 phải giữ generation OFF, chỉ mở thư viện, không bật snapshot override.

GET public mới ở [public-get-checks.json](public-get-checks.json), [public-evaluation-latest-get.json](public-evaluation-latest-get.json): frontend 200, health GET đầu timeout, ready/status sau đó 200; live fingerprint vẫn `83f93f...`, khác candidate PG. Một probe dùng URL archive không đúng trả 404 đã được giữ lại; endpoint đúng `/api/v1/evaluations/latest` trả 200. Không POST session/chat; chưa kiểm Turnstile/HMAC/SSE public. GET metadata không phải latency chat.

## 6. Pilot và ngân sách

[PILOT.md](PILOT.md), [pilot-plan.json](pilot-plan.json): **S01/S04/X01/N02/N07/N08**, 18 generation +4 judge =**≤22 requests**, phân bổ **40.000 tokens** nằm trong full allocation đề xuất 190.000, không cộng thành benchmark riêng.

Diagnostic retrieval cuối trên SQLite: **Recall@5=1.0, n=4** ca có gold của pilot; xem [pilot-retrieval-final.json](pilot-retrieval-final.json). IDs đã khóa trước measurement. Lượt ban đầu được giữ riêng vì policy/fingerprint khác; không gộp hoặc chọn điểm. Không có kết quả model Faithfulness, semantic Citation Accuracy, Answer Correctness, Answerable Coverage/False Abstention Rate hoặc model latency mới. Custom judge hiện có không được gọi là package Ragas.

## 7. Quyết định và bước tiếp theo

**NOT READY.** Cổng nguồn hoạt động và giữ fail-closed, nhưng phần lớn nội dung hiện hành chưa được duyệt; fixture không chứng minh model trả lời được các câu hỏi đủ nguồn. F03/S06 vẫn mở. PostgreSQL và public E2E còn thiếu bằng chứng.

Trình tự cần duyệt tiếp: chốt phạm vi hiện hành đủ cho demo → kiểm PostgreSQL/rollback riêng → freeze SHA/policy và duyệt pilot → review kết quả → mới quyết định rollout có kiểm soát. Không tiếp tục tối ưu S06. Phase 2B dừng tại đây để người dùng review; chưa phát hành bất kỳ thay đổi nào.
