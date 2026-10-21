# Changeset để review

HEAD/base: `117e7bd2c4a320c3d02256dfdabf858180b47dbf`. Không commit/push/deploy. Baseline working tree đã có F01/F03/Phase2; hash đầu vào ở `input-checksums.json`.

## Thay đổi trong Phase2B

| File | Trạng thái so với đầu vòng |
|---|---|
| `.dockerignore` | Đã chỉnh trong vòng này |
| `.gitignore` | Đã chỉnh trong vòng này |
| `backend/landlaw/agent.py` | Đã chỉnh trong vòng này |
| `backend/landlaw/api.py` | Đã chỉnh trong vòng này |
| `backend/landlaw/cli.py` | Đã chỉnh trong vòng này |
| `backend/landlaw/ops.py` | Đã chỉnh trong vòng này |
| `backend/landlaw/store.py` | Đã chỉnh trong vòng này |
| `docs/API.md` | Đã chỉnh trong vòng này |
| `docs/EVALUATION.md` | Đã chỉnh trong vòng này |
| `docs/OPERATIONS.md` | Đã chỉnh trong vòng này |
| `scripts/evaluate_generation_candidate.py` | Đã chỉnh trong vòng này |
| `scripts/package_release.py` | Đã chỉnh trong vòng này |
| `scripts/verify_source_gate_candidate.py` | Mới |
| `tests/test_citizen.py` | Đã chỉnh trong vòng này |
| `tests/test_claim_encoding.py` | Đã chỉnh trong vòng này |
| `tests/test_generation_source_policy_lock.py` | Mới |
| `tests/test_release_readiness.py` | Đã chỉnh trong vòng này |
| `tests/test_scoped_source_gate.py` | Mới |

- Source gate dùng app_state và source_reviews hiện có; không thêm migration hoặc pipeline. Receipt bind đúng chunk/date/checksum, chặn snapshot override và kiểm lại ở verify/finish.
- API/ops-status cho phép khả dụng theo phạm vi đã duyệt, không gọi toàn corpus là fresh. State schema giữ thông báo thiếu phạm vi qua các node.
- Helper evaluation nhập/khóa receipts, tránh restore xong rồi từ chối toàn bộ hoặc trộn source cohorts. Packaging giữ policy; thiếu receipt sau restore vẫn fail-closed.
- Hai fixture danh bạ đổi ngày UTC thành ngày Việt Nam; không đổi runtime danh bạ/verifier để làm test pass.
- Hai ignore files loại backup corpus local khỏi Git/Docker image; asset vẫn còn trên disk và đã bind checksum.
- Tài liệu API/Operations/Evaluation được cập nhật theo contract mới; số liệu nằm trong reports.

## Bảo vệ công việc trước đó

117 file thuộc evidence Phase1/Phase2, suite khóa và regression F03/F01 được so hash: không đổi. Xem `protected-input-verification.json`. `tests/test_agent.py` và `scripts/evaluate_faithfulness.py` đã sửa từ trước vòng này, giữ nguyên bytes đầu vòng. Không chỉnh các hàm clause-dependency/OR-AND hoặc prompt F03. S06 không gọi lại và không đổi verdict.

Artifact mới trong `reports/phase2b-rc-20261021/` lưu các lượt kiểm tra, kể cả lỗi harness, các policy ban đầu và policy cuối. Backup38MB bị ignore; `dist/phase2b-rc-20261021/` là asset local chưa publish. Chỉ stage report nhỏ và paths đã review; không stage credentials hoặc vector archive.
