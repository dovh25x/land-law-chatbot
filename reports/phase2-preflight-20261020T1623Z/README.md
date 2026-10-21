# Phase2 — Source Reliability, Deployment Readiness & Evaluation Preflight

Ngày20/10/2026, bắt đầu16:22:59UTC, timebox90phút. **Preflight đã thực hiện; chưa đủ điều kiện tuyên bố release/demo public E2E hoặc evaluation cuối đạt.** Không gọi Groq/judge, không commit/push/deploy, không ghi production database, không sửa corpus/embedding/credentials. F03 đóng vòng tối ưu; S06 giữ FAIL.

## Thay đổi thực tế

- `scripts/evaluate_faithfulness.py`: sửa lỗi mở store bằng cấu hình operator/owner, có thể ghi usage vào serving DB. Dùng SQLite tạm và xóa cả hai URL kết nối; giữ model/prompt/SAMPLE/công thức. Ghi judge identity riêng, đọc/giữ file cooldown qua database tạm để không bỏ mất giới hạn thực tế.
- `tests/test_faithfulness_isolation.py`:4 ca owner/non-owner × cooldown0/1giờ. Test trước vá chặn constructor và tái hiện2 failures; sau vá4 pass, cooldown đang còn thì0 provider calls. Chỉ FakeJudge.
- `docs/OPERATIONS.md`: làm rõ4 trạng thái, giới hạn snapshot override và receipt chưa import.
- `docs/EVALUATION.md`: làm rõ isolation/cooldown và phân biệt Recall@5 với @8, semantic accuracy với integrity.
- Thêm báo cáo/bằng chứng Phase2, receipt **đề xuất** QĐ56 và sidecar taxonomy **để review**, không đổi gold/suite. Không thay bất kỳ code/test F01/F03 có sẵn khi bắt đầu Phase2; kiểm tra checksum cuối ở `final-verification.json`.

## Repository và deployment

HEAD local `117e7bd2c4a320c3d02256dfdabf858180b47dbf`, working tree chứa các patch Phase1 chưa commit. Local SQLite fingerprint `2dab4dde…`, PostgreSQL candidate `c5008efb…`; live GET báo `83f93f64…`. Không coi patch local đã có trên cloud. SHA cloud chưa xác minh trực tiếp control plane; số liệu d2424ed trong report cũ là lịch sử.

Corpus local/live cùng `corpus-a26bc99e541fbbe2`,60 documents/7.392 chunks. Readyz live báo PostgreSQL và key configured, status cho phép generation nhưng source_fresh=false. Archive evaluation không khớp active runtime/corpus. Không chuyển điểm cũ để chứng nhận candidate.

## Source reliability

Xem [bảng nguồn, ngày và quan hệ pháp lý](SOURCE_REVIEW.md). Audit disposition **59 stale/1unknown/0fresh/0new-confirmed-changed**; không cấp freshness bằng HTTP200/hash trùng.13 trang trọng tâm được GET,6 bản gốc tải lại khớp. QĐ56 trả403; receipt unavailable thử trong SQLite riêng cho kết quả unknown, không được source_fresh chấp nhận. Production chưa import receipt.

QĐ40 Điều2 xác nhận thay các QĐ47/2016,56/2024,38/2025,10/2026 từ02/04/2026. QĐ10 chỉ bãi Điều2 QĐ38 ở thời điểm tháng1; QĐ566 đính chính một phần QĐ10. NĐ49 phải đọc cùng NĐ88/NĐ151/NĐ226 và điều chuyển tiếp. Các mốc này không chứng nhận mọi nội dung còn áp dụng ngày20/10. Chưa rà trực tiếp47nguồn còn lại, chưa đối chiếu lại15ảnh NQ254 hoặc đầy đủ mọi sửa đổi mới.

## Tests/build và phạm vi

| Kiểm tra thực tế | Kết quả | Evidence/giới hạn |
|---|---|---|
| Backend trước sửa Phase2 |399 pass |`backend-tests.log`, Python3.14.4 |
| Backend sau sửa |403 pass |`backend-tests-final.log`, giữ399 regression cũ |
| Python3.12.15, đúng requirements.lock |403 pass |`python312-backend-tests.log`; venv tạm, không thay .venv/lock |
| Frontend unit |14 pass |`frontend-tests.log` |
| Frontend build |pass |`frontend-build.log` |
| Playwright local desktop/mobile |100 pass |`frontend-e2e.log`; API fixtures, **không public E2E** |
| Corpus integrity/parser offline |60/60 tái lập,0error/0warning |`corpus-audit.json`;133 raw files, gold không thiếu, không embedding lại |
| Receipt mapping/restore local |pass,60stale→59stale+1unknown |`source-policy-replay.json`, Python3.12/SQLite tạm |
| Public GET |root200; lần đầu backend timeout20s, lần sau4endpoint200 |`read-only-http-checks.json`, `deployment-warm-get.json`; không chat/model |
| Secret scan/diff/protected files |Xem kết quả cuối |`secret-scan.log`, `diff-check.log`, `final-verification.json` |
| Docker512MiB, PostgreSQL restore/role/cloud E2E mới |**Chưa kiểm thử** |Docker WSL không dùng được; không tạo DB/cloud resources trong vòng này |

Python3.12 đã có trên máy nhưng ngoài PATH; cache offline thiếu package nên giữ log lần setup thất bại. Sau đó cài đúng72 package khóa vào `/tmp/landlaw-phase2-py312` qua cơ chế thực thi được phép, không nâng dependency. Không dùng CI/image cũ để chứng nhận code chưa commit.

## Deployment readiness checklist

[Checklist chi tiết và manual flow](DEPLOYMENT_CHECKLIST.md) phân biệt code review, test local và GET live. Signed ingress/Turnstile/quota/timeout/IndexedDB có tests, nhưng chưa xác minh lại env/DB role/negative origin trên cloud. Manual flow còn thiếu: mở website → Turnstile thật → câu hỏi giả lập ngoàiS06 → verified result → citation → follow-up → reload → xóa lịch sử. Cần approval riêng vì tạo session/ghi metadata và có thể gọi model. GET sau khi backend phản hồi không thay test cold-start/chat.

## Evaluation preflight

[Kế hoạch chi tiết](EVALUATION_PREFLIGHT.md) giữ32ca, sidecar đề xuất19answerable/5needs-facts/4out-of-scope/2missing-source/2safety-meta.20ca có gold đủ để đo retrieval. Không sửa gold hoặc loại S06. @5 chưa đo; custom faithfulness không phải package Ragas; citation integrity chưa phải semantic citation accuracy. Chấm correctness theo rubric/checksum và tách answered/correct-refusal/false-refusal/limited/missing.

Ngân sách **đề xuất**, không phải dự báo benchmark: pilot tối đa6ca,36requests/60.000tokens nằm trong tổng;31ca khôngS06 tối đa186generation requests, phân bổ150.000tokens; sample judge tối đa16requests,40.000tokens. Trần tổng202requests/phân bổ190.000tokens chưa chắc hoàn thành được bộ và không bảo đảm quota thực còn đủ. Concurrency1, giữ6requests/90s và cooldown. Không bắt đầu khi chưa chốt quota/case IDs; không chạy nền/resume để chọn điểm đẹp. Chỉ reuse S06 đã fail nếu cùng đầy đủ identity/backend; cohort PostgreSQL mới thiếu S06 vẫn giữ mẫu số32 và ô missing.

## Release blockers

| Mức | Phát hiện và điều kiện xử lý |
|---|---|
| **BLOCKER B01** |Chưa đủ evidence/receipt cho khẳng định pháp luật hiện hành2026; live source_fresh=false, QĐ56 không truy cập được. Rà nguồn ưu tiên, duyệt receipt thật, giữ unknown fail-closed; không sửa checked_at để vượt cổng |
| **BLOCKER B02** |Live fingerprint khác candidate, F01 mới chỉ được chứng minh local. Review/commit SHA sau approval, CI rồi deploy đúng SHA và xác minh lại; không giả patch đã live |
| **BLOCKER B03** |Public end-to-end chưa có bằng chứng, chưa thể bảo đảm demo. Manual challenge/chat/citation/history/delete với câu hỏi và quota được phê duyệt |
| **MUST_FIX M01** |Chốt SHA/env/ingress/quota/DB role/persistence/backup restore/image memory của bản sẽ nộp. Readiness HTTP200 không chứng minh tất cả |
| **MUST_FIX M02** |Review taxonomy sidecar, chuẩn hóa @5 và semantic citation review, khóa scorer/receipt/backend identity trước evaluation. Giữ missing/error/fail đúng mẫu số |
| **MUST_FIX M03** |Trước dùng judge thật: lưu mọi attempt/checkpoint trước resume, giữ cooldown và kiểm soát budget toàn đợt. Có thể chọn review thủ công mẫu để tránh thêm quota; không tự gọi API |
| **DEFER D01** |Tối ưu thêm F03/S06: dừng theo quyết định, giữ FAIL và khả năng guard false positive80ký tự như hạn chế; không mở lại tuning |
| **DEFER D02** |Framework/model/reranker/multi-agent/GIS, corpus đa dự án, giá tiền/thửa đất và candidate nguồn mới chưa duyệt; không cần cho MVP hiện tại |

## Thứ tự tiếp theo trước23/10/2026

1. Review diff Phase1+Phase2, receipt đề xuất và phạm vi demo. Chốt SHA/source-policy; chỉ sau approval mới commit/push/deploy hoặc import production receipt.
2. Ưu tiên nguồn trực tiếp điều chỉnh demo Hà Nội2026: QĐ40 và chuỗi thay thế/đính chính, NĐ49/NQ254 và luật chung. Giữ phần chưa rà là stale/unknown, không cấp freshness hàng loạt. Có thể giữ profile học thuật với phạm vi/hạn chế trung thực; không tuyên bố full quality gate đạt.
3. CI/image/restore riêng cho bản ghim, deployment parity và manual public E2E. Chuẩn bị warm-up demo và thông báo quota/timeout, không đổi hosting/model để né rủi ro.
4. Duyệt kế hoạch model evaluation theo batch/quota và backend riêng; không gọi lại S06. Review nguồn/citation/checksum, xuất5metrics với coverage/limitations, không dùng số cũ chứng nhận fingerprint mới.
5. Hoàn thiện báo cáo học thuật: PRD/phạm vi, kiến trúc, phương pháp RAG/corpus/provenance, thiết kế và kết quả evaluation, phân tích lỗi S06/abstention, runbook triển khai/backup, hướng dẫn demo và giới hạn pháp lý. Ghim source/package/corpus/evidence cho nộp bài; không cần thêm tính năng phổ biến.

Đây là báo cáo kỹ thuật, không phải thẩm định pháp lý độc lập. Đợt này dừng để chủ dự án review, không tự thực hiện bước phát hành hoặc model evaluation tiếp theo.
