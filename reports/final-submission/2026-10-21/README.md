# Final submission — Hanoi Land Law Assistant

**Bản thảo nộp đồ án, chốt evidence 21/10/2026. Deployment: NOT READY.** Thông tin bìa/học phần để trống theo yêu cầu. Gói này không tạo commit, push, deploy hoặc gọi Groq/judge. Không có model-answer pass được xác nhận trên runtime cuối.

## Tài liệu để review

| Tài liệu | Nội dung |
|---|---|
| [Final project report](FINAL_PROJECT_REPORT.md) | Báo cáo tiếng Việt 12 chương, cơ sở lý thuyết, kiến trúc thực, kết quả và references; chưa PDF/DOCX |
| [Slide outline](SLIDE_OUTLINE.md) | 12 slide, khoảng 10 phút; chưa PPTX/PDF |
| [Demo script](DEMO_SCRIPT.md) |5–7 phút source/retrieval evidence, fixture có nhãn, hỏi thêm/từ chối và fallback |
| [Evaluation summary](EVALUATION_SUMMARY.md) | Tách từng lớp/case/cohort, công thức mẫu số, metrics chưa đo |
| [Known limitations](KNOWN_LIMITATIONS.md) | Giới hạn pháp lý/kỹ thuật và threats to validity |
| [Release checklist](RELEASE_CHECKLIST.md) | PASS/FAIL/NOT TESTED; release/rollback có điều kiện |
| [Submission checklist](SUBMISSION_CHECKLIST.md) | Việc còn thiếu trước nộp, asset ignored và ước lượng |
| [Evidence index](EVIDENCE_INDEX.md) | Liên kết artifact gốc và checksum máy đọc |
| [Code freeze](CODE_FREEZE.md) | Phân loại toàn bộ thay đổi cần giữ, file riêng tư và lệnh sau review |

## Những gì thực sự xác nhận

- 516 backend regression tests trên Python 3.14.4 từ Phase 3B và 516 trên Python 3.12.15 testtools image trong Phase 4; không cộng hai lần thành 1.032 test độc lập. Lần đầu trong serving image có 513 pass/3 fail do thiếu Git/notebook, giữ log gốc.
- 14 frontend unit tests, build và 100 Playwright local fixture tests từ Phase 3B; source frontend không đổi. Chưa public E2E candidate.
- SQLite 19 câu: macro Recall@5 **97,37%**,20/21 gold hits, micro **95,24%**. Không phải answer accuracy.
- Final context C02 **3/3**, C03 **7/7** required units; quote fixture có nguồn hợp lệ. Không phải model-answer pass.
- Theo chấp thuận mở Docker: serving image build/probe/memory **PASS local** (382,66 MiB peak RSS, giới hạn 512 MiB); PG 16.15/pgvector 0.8.7 local **PASS** migrations/role/session lease/corpus backup-restore. Container PG được dừng, dữ liệu giữ lại; không cloud/production.
- S06 **FAIL**; C01 **INCOMPLETE**; C02/C03 **NOT RUN trong Phase 3A**. Final-runtime model correctness, Citation Accuracy, RAGAS, faithfulness/coverage/false-abstention rates và public latency **NOT MEASURED**.

## Danh tính và kiểm chứng

[freeze-manifest.json](freeze-manifest.json) có HEAD nền, source-tree hash dirty, runtime/corpus/receipt/suite/image identities. HEAD nền `117e7bd…` chưa chứa toàn bộ patch; candidate commit vẫn null. [validation.json](validation.json) kiểm checksum core/history và links; [evidence-index.json](evidence-index.json) băm các artifact được dẫn. [Docker](docker-preflight.json) và [PG](postgres-preflight.json) là evidence mới, không thay các receipt NOT RUN lịch sử.

Từ repository root, kiểm lại read-only nội dung nguồn/evidence, chỉ ghi receipt validation trong thư mục này:

```bash
.venv/bin/python reports/final-submission/2026-10-21/verify_submission.py
```

Script không gọi API, không đọc credentials, không đổi database hoặc runtime. Các script PG/image kèm theo chỉ là harness đã chạy trên môi trường cách ly; không tự chạy lại, không dùng `.env` production. Không nhân bản cây reports; giữ cấu trúc repo để link nội bộ còn đúng. Backup PG local 39 MB là corpus/config cho restore proof, không cần nhúng trong PDF/slide, giữ riêng khi giao gói đã review.

## Điều kiện còn thiếu

Trước deploy: review/commit đúng source, CI/registry image theo SHA mới, scope nguồn phù hợp ngày demo, PG cloud/backup/role và rollback tuple, public ingress/Turnstile/E2E; quyết định generation có được mở khi chưa có model pass. Allocation cũ còn 7.841, nhỏ hơn reservation C02 cần 19.788; không tự reset/refund unknown hoặc chạy pilot.

Trước nộp: đọc duyệt báo cáo, điền bìa khi có thông tin, đối chiếu rubric nếu được cung cấp, xuất PDF/slides, rehearsal, giao đủ asset/hash và kiểm archive/secret/link cuối. Ước lượng **5,5–9 giờ** công việc học thuật; cloud thêm **4–8 giờ** nếu không gặp blocker quyền/quota/restore. Đây là ước lượng, không bảo đảm completion hoặc điểm học phần. Chi tiết ở submission checklist.
