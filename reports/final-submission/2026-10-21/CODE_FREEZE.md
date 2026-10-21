# Code freeze và phân loại working tree

Freeze Phase 4 không tạo commit. HEAD nền là `117e7bd2c4a320c3d02256dfdabf858180b47dbf`; **HEAD này chưa chứa toàn bộ patch đang dirty**. Candidate được nhận diện bằng source-tree SHA, corpus/receipt/suite hashes và runtime fingerprints trong [manifest](freeze-manifest.json). Không phát hành chỉ bằng SHA nền.

## Những thay đổi cần giữ

| Nhóm | Files chính đang thay đổi hoặc untracked | Lý do giữ và evidence |
|---|---|---|
| F01/scoped source gate | `backend/landlaw/store.py`, `ops.py`, `cli.py`, `api.py`; `tests/test_source_review_policy.py`, `test_scoped_source_gate.py` | Phân biệt changed/stale/unknown, receipt checksum/date scope; source gate fail-closed. Snapshot override không hợp thức hóa nguồn known-changed. |
| F03/clause dependency/OR-AND | `agent.py`, `synthesis_context.py`; `test_clause_dependencies.py`, `test_alternative_condition_logic.py`, `test_s06_clause_context.py`, fixture S06 | Regression tổng quát và guard; S06 vẫn FAIL, không xóa fixture hoặc sửa để làm pass. |
| Phase 2C/2 D coverage/context | `data/legal_relations.json`; `scripts/prepare_current_legal_candidate.py`, `verify_current_legal_coverage.py`, `verify_source_gate_candidate.py`, `verify_synthesis_integrity.py`; tests/fixtures current-source, `test_current_legal_candidate.py`, `test_synthesis_integrity.py` | Review dependencies và actual synthesis ledger; không re-embed/corpus-edit trong Phase 4. |
| Phase 3B API reliability/accounting | `provider.py`, `request_budget.py`, `evaluation.py`; `scripts/evaluate_generation_candidate.py`; `test_request_budget.py` | Reservation bảo thủ, confirmed/unknown tách biệt, format failure bounded và retry/cooldown;30 tests. |
| Evaluation isolation/release scripts | `scripts/evaluate_faithfulness.py`, `package_release.py`; `test_faithfulness_isolation.py`, `test_generation_source_policy_lock.py`, `test_release_readiness.py` | Không trộn judge budget/candidate source policy, không ghi đè receipt; giữ historic attempts. |
| Tests phụ thuộc | `tests/conftest.py`, `test_agent.py`, `test_citizen.py`, `test_claim_encoding.py`, `test_quality_candidate.py` | Fixtures khai báo nguồn thực sự xuất hiện; không nới runtime verifier. |
| Hướng dẫn/ignore | `docs/API.md`, `docs/EVALUATION.md`, `docs/OPERATIONS.md`, `.gitignore`, `.dockerignore` | Contract, vận hành, privacy và đóng gói. Không thay credentials/dependencies. |

Toàn bộ path/bytes chính xác được khóa trong `freeze-manifest.json`, không chỉ bảng ví dụ này. Phase 4 đối chiếu 201 source files với baseline Phase 3B; chỉ `.dockerignore` đổi. Không tuyên bố đã tái audit pháp lý từng dòng toàn bộ repository trong vòng freeze.

## Thay đổi riêng Phase 4

- Thêm bộ tài liệu trong thư mục này, index/checksum và các script kiểm chứng offline của bộ nộp.
- `.dockerignore`: loại `reports/final-submission/` và bản backup trùng `reports/phase3b-*/local-corpus-backup.json` khỏi image. API đọc `reports/latest.json`/`public-evaluations.json`, không tham chiếu các đường dẫn bị loại. Backup vẫn còn trên đĩa; không xóa evidence.
- Theo chấp thuận bổ sung khi Docker Desktop mở: build image local, chạy memory fixture network-none, PostgreSQL container mới và testtools image riêng để kiểm Python 3.12. **Không sửa runtime logic**, Dockerfile serving, source data hay project dependency locks.

## Artifacts và dữ liệu cần giữ, không stage bừa

| Loại | Đường dẫn | Xử lý khi nộp/release |
|---|---|---|
| Bằng chứng gốc | `reports/phase1-*`, `phase2-*`, `phase2b-*`, `phase2c-*`, `phase2d-*`, `phase3a-*`, `phase3b-*`, historical `reports/evaluation/` | Giữ tất cả, kể cả FAIL/INCOMPLETE, source-before và request receipts. Index liên kết, không nhân bản cả cây vào package mới. |
| Candidate/nguồn public đã xử lý | `data/staging/phase2c-current/release-v5.json`, provenance và receipts/policy Phase 2C | Asset bị ignore cần kênh giao riêng được kiểm/hash; không nghĩ `git add .` sẽ giao đủ hoặc an toàn. |
| Backup corpus/config local | Backup 39 MB Phase 3B và PG backup mới nếu tạo | Giữ tại chỗ, checksum và link; không copy sang slide/PDF hay serving image; không có sessions/messages. |
| Model/checkpoint local | `models/e5/`, `data/checkpoints/` | Không commit binary; hướng dẫn download/checksum hiện có. Không re-embed. |
| Logs/build output | `frontend/dist/`, test results, các log Phase 4 | Build output có thể ignore; logs dùng để review, không giả là CI artifacts của commit mới. |
| Secret/private runtime files | `.env*`, databases local, auth/token/cookie files | Không đưa vào gói nộp hoặc git/image; không in giá trị. Không đổi cấu hình production. |

Baseline khóa 2.906 historical report files. Validation cuối so SHA và sự tồn tại; không ghi vào artifact cũ. Các kết quả Phase 4 là sidecar mới, không “sửa” receipt cũ để phù hợp fingerprint hiện tại.

## Lệnh chuẩn bị sau review — CHƯA THỰC THI

Không dùng `git add .` hoặc lệnh sửa/xóa dữ liệu. Người vận hành phải review patch và chọn danh sách path từ manifest/index, tách asset public khỏi secrets; các lệnh dưới là khung, không có quyền tự chạy:

```bash
git status --short
git diff --check
git diff -- .dockerignore backend/landlaw scripts tests data/legal_relations.json docs
# Sau review: git add -- <danh-sach-file-da-duyet>
git diff --cached --stat
git diff --cached --check
# Sau phê duyệt commit: git commit -m "Prepare final project release candidate"
# Ghi SHA thực vào một release manifest mới; không sửa manifest lịch sử.
# Sau phê duyệt push: git push <remote-da-xac-minh> <branch-da-duyet>
# Sau CI và deploy approval: dùng đúng runbook/workflow hiện có theo SHA mới.
```

Không có SHA tương lai có thể đoán chính xác trước commit. `candidate_commit=null` là dữ kiện, không lỗi để điền SHA nền. Deploy helper có thể từ chối source dirty; không tắt check hoặc quality guard để vượt qua.

## Khôi phục và rollback

Trước mọi thay đổi tiếp theo, giữ bản freeze này và source/evidence hashes. Các bản `source-before` Phase 3B chỉ phục vụ diff/reproduction, không tự coi là cloud rollback an toàn. Rollback vận hành cần tuple source/image/corpus/policy/receipt/schema đã thử, chưa có proof production cho candidate này. Quy trình và điều kiện chặn ở [release checklist](RELEASE_CHECKLIST.md). Không reset working tree của người dùng, không drop DB hoặc phục hồi server history cũ.
