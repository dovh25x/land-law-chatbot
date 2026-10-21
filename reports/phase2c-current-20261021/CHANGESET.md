# Changeset Phase2C để review

Phân biệt delta Phase2C với workingtree có sẵn từPhase1/2B. Không reset/ghi đè thay đổi của người dùng.

| File | Thay đổi Phase2C |
|---|---|
|`backend/landlaw/agent.py`|Nhận diện từ địa bàn, gắn điều với đúng văn bản, phân biệt ngày và số văn bản; mở guides theo điều nguồn, ưu tiên căn cứ đã review và giữ parent/điều khác trong cap16. Không đổi prompts/verifier/F01/repair/provider.|
|`backend/landlaw/store.py`|Ưu tiên đoạn đã được scope receipt chấp nhận trong pool retrieval hiện có; không thay source review states/admission và giữ fallback cho guard từ chối.|
|`data/legal_relations.json`|8guides về căn cứ bồi thường/hỗ trợ/tái định cư; phạm vi đầy đủ bãi bỏ49→226 ở điều/khoản/gạch đầu dòng.|
|`scripts/prepare_current_legal_candidate.py`|Prep offline4đoạn nguyên văn có provenance; chỉ4vector mới, bảo toàn dữ liệu/vector cũ và tạo immutable candidate mới.|
|`scripts/verify_current_legal_coverage.py`|Harness SQLite riêng, khóa input/runtime, chặnHTTP; planner/draft/semanticjudge fixture ghi rõ, không có live mode.|
|`tests/test_current_legal_candidate.py`|24regression cases về scope/provenance/citation/routing/retrieval.|
|`tests/fixtures/current-source-provisions.json`|Các đoạn luật công khai tối thiểu cho regression; không fullcorpus hoặc credentials.|
|`reports/phase2c-current-20261021/`|Review,receipts cuối,provenance,attempts cảfail/pass,tests,manifest,deploy/rollback,pilot. Chỉ finalmanifest/receipts-final/source-gate-final dùng chocandidate.|

Không sửarawdata,embedding/model/credentials/migrations/frontend hoặc gold20+4+8. Snapshot gốc60docs/7392chunks giữ nguyên; assetcandidate60docs/7396chunks chỉ ởstaging/distlocal, chưaproduction.

Các proposal/candidatev1–v4 có đoạn toàn7(2a) NĐ226 bao gồm hai gạch bị bãi bỏ; **không được phát hành**. Candidatev5 vàreceipts-final đã thu hẹp đúng gạch thứ5, bổ sung nguyên văn49:16(3g) và vẫn giữ yêu cầu citation49.

Checkpoint2/3 và mọi attempt không đạt giữ nguyên. S06FAIL thật không bị sửa/chạy lại. Lần thêm phân bổ context cho3/3 structuralfixture. Review projection sau đó phát hiệnC01/C03 vẫn thiếu căn cứ ở đầu vào synthesis; fixture dùng rawID retrieval nên không chứng minh pipeline/modelpass. Giữ dữ liệu gốc và bổ sung review, không sửa/xóa kết quả để che blocker.

Danh sáchstage dự kiến ở`reviewed-paths.txt` gồm cảpatchPhase1/2B chưacommit; cần người dùng review toàn changeset trước lệnhgit. `git add`/commit/push/deploy chưa chạy.
