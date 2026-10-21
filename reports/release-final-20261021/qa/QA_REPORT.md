# QA/Evidence — final release candidate

Đối chiếu ngày 21/10/2026, giờ Việt Nam. Báo cáo chỉ mô tả evidence đã kiểm tra; không chứng nhận triển khai cloud hoặc chất lượng đáp án model.

**Cập nhật sau baseline:** C02 allocation độc lập đã chạy một attempt, kết quả **INCOMPLETE**; xem [QA pilot](c02-pilot-review.md). Sau đó root giao triển khai safe fallback đã được user cho phép. Fallback source-only hiện **đã triển khai và PASS local acceptance**, không còn chỉ là đề xuất; xem [bản vá và tests](SOURCE_LOOKUP_PATCH.md), [actual API receipt](source-lookup-acceptance.json). Các mục dưới đây mô tả thời điểm baseline trước fallback; không dùng chúng để kết luận code mới vẫn có fingerprint1697 hoặc chưa có verified-only view. Cloud/public E2E do release owner xác minh riêng.

## Kết quả đã xác minh

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| 201 source paths so với Phase 4 freeze tại thời điểm đầu vòng QA | PASS | Không có thay đổi byte ở thời điểm `candidate-verification.json`; sau đó release owner bổ sung packaging ignores, cần freeze mới |
| 2.906 artifacts lịch sử | PASS | SHA256 khớp toàn bộ baseline, không sửa/xóa để đổi kết quả |
| 45 file được seal trong Phase 4 | PASS | Đối chiếu `SHA256SUMS`, không chạy lại verifier Phase 4 vốn ghi vào lịch sử |
| Corpus, source policy, receipt bundle, evaluation suites và locks | PASS | Hash khớp freeze; không thay gold, corpus hoặc nguồn |
| Runtime fingerprint SQLite | PASS | `1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d` |
| Secret scan | PASS tại thời điểm kiểm tra | `scripts/check_secrets.py`, gồm source và public frontend assets; cần release owner chạy lại sau khi các tác vụ ghi file kết thúc |
| Git diff whitespace | PASS tại thời điểm kiểm tra | `git diff --check` |
| Restore vào SQLite riêng không có receipts | PASS, fail-closed | Không dùng DB production; receipt replay chỉ ghi vào `qa/source-scope-private.db`, không đưa DB vào Git |
| 74 passage IDs có exact checksum trong snapshot | PASS | Không suy ra cả 74 đang áp dụng cùng thời điểm |
| Exact interval admission trên 4 ngày × 74 passages | PASS, 296 comparisons | Khớp tất cả khoảng `as_of_from <= date < as_of_to` đã được review |

Receipt và raw stdout ở cùng thư mục. `candidate-verification.json` là ảnh chụp trước thay đổi packaging của release owner, không phải manifest commit cuối.

## Các kết quả software được tái sử dụng hợp lệ

Không chạy lại cùng tests khi byte runtime, frontend, dependencies, migrations và gold chưa đổi. Các thay đổi packaging mới cần image/CI của candidate cuối; chúng không tự tạo ra model evidence.

| Evidence | Kết quả | Giới hạn |
|---|---|---|
| Phase 4 Python 3.12 testtools image | 516 passed | Git được cài trong test-only layer, notebook mount read-only. Serving image ban đầu 513 passed/3 fail vì thiếu Git/notebook được giữ nguyên |
| Phase 3B Python 3.14 | 516 passed | Cùng project code/packages trước packaging-only delta; không cộng với 516 của Python 3.12 thành 1.032 tests |
| Frontend unit | 14 passed | Vitest local |
| Frontend build | PASS | Vite/TypeScript, không phải public site |
| Playwright local | 100 passed | API mocks/local browser, không chứng nhận Turnstile hoặc signed public ingress |
| Docker serving image | PASS local | Image/probe/memory của Phase 4; image mới cần identity mới nếu thay build context |
| Memory | 382,6640625 MiB peak RSS | Recorded Python 3.12 fixture workload, hard cap 512 MiB; không phải bảo đảm mọi cloud workload |
| PostgreSQL 16/pgvector local | PASS | Migrations 001–006, runtime role, lease, corpus backup/restore, receipt restore; không phải Supabase/cloud |

## Phạm vi nguồn và ranh giới ngày áp dụng

SQLite replay riêng cho kết quả:

| Thời điểm hỏi | Fresh | Unknown | Diễn giải |
|---|---:|---:|---|
| 02/08/2024 | 25 | 49 | Phạm vi lịch sử được review; không phải mọi câu hỏi lịch sử đều trả lời được |
| 21/10/2026 | 43 | 31 | Có các passages nghiệp vụ phục vụ tình huống C01/C02/C03 đã định nghĩa |
| 22/10/2026 | 1 | 73 | Chỉ còn header QĐ40 có khoảng review riêng; không đủ các căn cứ nghiệp vụ đã chọn |
| 23/10/2026 | 1 | 73 | Không tự có current-law coverage vào ngày deadline |

`source_gate_status.usable=true` đếm hợp passages được review ở các khoảng khác nhau; không được dùng nó để khẳng định mọi passage hoặc ngày hiện tại đều fresh. Việc phát hành claim thực tế vẫn kiểm exact chunk/date bằng `scoped_source_reviews`.

Lần kiểm đầu có hai FAIL do giả định của QA rằng không còn bất kỳ passage fresh nào sau 21/10. Thực tế header `qd-40-2026-hanoi-0-2-0` có scope explicit 01/01–28/10. Giữ `source-scope-date-verification.json` FAIL và `extended-scope-explanation.json`; kiểm đúng explicit intervals ở `source-scope-exact-interval-verification.json` PASS. Không sửa runtime/receipts/corpus để đạt PASS. Header fresh không chứng minh nội dung quyền lợi ngày 23/10.

Điều 104 lịch sử được review vẫn `unknown` tại 21/10, đúng fail-closed. Khả năng đọc thư viện snapshot không đồng nghĩa khả năng phát hành kết luận luật hiện hành.

## Evaluation integrity

Recall@5 SQLite từ cùng fingerprint cuối: macro `sum(hits_i/gold_i)/19 = 0,9736842105263158`, tức **97,37% trên 19 câu**; micro `20/21 = 0,9523809523809523`, tức **95,24%**. Chỉ là retrieval trên tập có gold labels và exclusion đã khai báo; không phải legal-answer accuracy, PostgreSQL recall, answerable coverage hoặc số câu model trả lời đúng.

Giữ nguyên **S06 FAIL**, **C01 INCOMPLETE**, **C02/C03 NOT RUN trong Phase 3A**. Nếu có C02 allocation mới, kết quả phải ghi riêng attempt, ngân sách, fingerprint và timestamp, không ghi đè Phase 3A hoặc chọn lần đẹp. QA không gọi model/API.

Citation integrity fixture/capture PASS chỉ chứng minh ánh xạ source snapshot, chunk, locator và excerpt. Không thay semantic Citation Accuracy hoặc đánh giá pháp lý độc lập. Final-runtime Answer Correctness aggregate, RAGAS Faithfulness, False Abstention Rate và latency model tổng quát vẫn NOT MEASURED khi chưa có evidence mới.

## Release checks cần release owner hoàn thành

1. Tạo manifest theo commit cuối, đối chiếu packaging-only delta `.gitignore`/`.dockerignore`; không đổi Phase 4 freeze lịch sử.
2. Không commit SQLite replay 116 MiB, backup corpus 39 MiB, credentials hoặc build caches. Delivery corpus phải qua asset được checksum và restore kiểm chứng, không giả định clone tự có file ignored.
3. CI chạy trên SHA đã push và image identity cuối; Phase 4 image local không tự đại diện SHA cloud mới.
4. Kiểm cloud runtime role/schema và backup/restore/rollback thực tế trước khi activate candidate. Không suy local PG PASS thành cloud PG PASS; migration 006 không có rollback về server history.
5. Giữ source review đúng ngày hỏi. Câu hỏi 21/10 được review không trở thành kết luận hiện hành cho ngày 23/10 nếu chưa có review mới.
6. Public E2E phải có browser thật, Turnstile tương tác người dùng, signed ingress, citation links, follow-up, reload/clear và mobile. Local mocks không đủ.

## Safe fallback có sẵn và phần chưa có

`GENERATION_ENABLED=false` hiện làm `/api/v1/chat` trả HTTP503 `generation_disabled`; không tự trở thành extractive chat. Thư viện `/documents` và `/documents/{id}` hiện hiển thị snapshot gồm cả nguồn chưa được review, nên chỉ có thể gọi là thư viện tham khảo có nhãn giới hạn.

Nếu release owner cần verified-only source lookup, thay đổi nhỏ phải lọc exact chunks bằng receipt checksum và ngày hỏi, hiển thị nguyên văn/nguồn/ngày, không suy luận quyền lợi. Không lọc chỉ theo whole-document freshness hoặc `source_gate.usable`. Chỉ được gọi đây là chế độ đã có khi patch, tests và public evidence thực sự tồn tại.

**Quyết định QA tại thời điểm báo cáo: source/evidence integrity PASS; cloud deployment và public E2E NOT TESTED; chưa đủ bằng chứng chứng nhận deployment-ready hoặc chất lượng legal answers.**
