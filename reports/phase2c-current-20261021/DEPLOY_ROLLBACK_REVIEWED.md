# Kế hoạch commit, deploy và rollback — chưa thực thi

Chỉ thực hiện sau khi người dùng duyệt changeset, phạm vi pháp luật, các gate còn thiếu và cấp quyền riêng cho push/deploy/Groq. Không dùng HTTP200 hoặc fixture pass làm release-ready.

## Blocker bổ sung trước pilot/deploy

Review projection cuối: C01 thiếuNQ254 vàC03 thiếuND88/ND49 trong bounded synthesis input. Structural fixture có thể cite rawID ngoài phần expose cho model; không phải pipelinepass. Chưa triển khai ba nhóm đầy đủ, không nên dùng quota để xác nhận một kết luận3/3 không hợp lệ. Giữ nguyên verifier/cap/gold và khép blocker trước rollout. Xem`release-manifest-reviewed.json` và`synthesis-projection-review.json`.

## Freeze và commit sau review

```bash
git diff --check
git switch -c phase2c/current-legal-coverage-rc
git add --pathspec-from-file=reports/phase2c-current-20261021/reviewed-paths.txt
git commit -m "Recover scoped current legal coverage and bind source dependencies"
git rev-parse HEAD
```

`117e7bd` chỉ là base, chưa chứa các patch. Commit SHA chưa thể biết trước khi commit; manifest dùng source-tree checksum và để candidate_commit_sha=null. Sau commit, ghi SHA thực40ký tự vào manifest mới, giữ manifest trước review, kiểm source hashes khớp và chạy lại nếu code/config đổi. Không dùng git add . hoặc đưa data/staging/models/.env vào commit.

Chỉ sau quyền push:

```bash
git push -u origin phase2c/current-legal-coverage-rc
```

## PostgreSQL riêng và asset

Chưa kiểm migration/runtime role/pgvector/backup-restore của candidate trênPostgreSQL. Helper hiện có tạo database thử nghiệm trên instance cấu hình, nên cần duyệt quyền trước khi chạy:

```bash
.venv/bin/python scripts/verify_postgres_database.py \
  --source dist/phase2c-current-20261021-context-pack/corpus-backup.json \
  --output reports/phase2c-postgres-NEW/restore.json
```

Không chạy trên serving database; không DROP. Helper chưa áp dụng receipts: nhập đúng `receipts-final`/`source-gate-final.json` vào chính testDB; kiểm quyền runtime đọc source_reviews/app_state và không sửa policy, restore thiếu receipts phải fail-closed. Kiểm migration ledger;006 không phải thao tác an toàn để chạy lại thử trên production. Candidate không đổi schema/vector dimensions.

Giữ backup corpus/config production, receipts hiện hành và previous Release riêng. Kiểm dung lượngPostgreSQL dự kiến khi giữ cả hai release theo giới hạn350MB; chưa đo capacity production trong vòng này. Chỉ gỡ release cũ sau rollout và restore đạt.

Local artifact chuẩn bị bằng `scripts/package_release.py` được nêu trong manifest; source-review ZIP phải chứa CHỈ policy/receipts-final đã bind hash. Các candidate v1–v4 và receipts proposal đều không dùng để deploy: đã có lỗi được giữ làm bằng chứng. Đặc biệt bản trích toàn7(2a) chứa hai gạch bị bãi bỏ, đã thay bằng gạch thứ5 trong candidate cuối.

Nếu cần GitHub Release sau approval, tạo tag mới theo SHA và upload corpus-backup.json, manifest.json, SHA256SUMS và source-reviews-final.zip. Không overwrite asset/tag cũ. Ví dụ:

```bash
CANDIDATE_GIT_SHA='SHA_40_KY_TU_DA_KIEM_THU'
CANDIDATE_RELEASE_TAG=phase2c-rc-$CANDIDATE_GIT_SHA
gh release create "$CANDIDATE_RELEASE_TAG" \
  dist/phase2c-current-20261021-context-pack/corpus-backup.json \
  dist/phase2c-current-20261021-context-pack/manifest.json \
  dist/phase2c-current-20261021-context-pack/SHA256SUMS \
  dist/phase2c-current-20261021-context-pack/source-reviews-final.zip \
  --target "$CANDIDATE_GIT_SHA" --draft --title "Phase 2C scoped candidate"
```

## Rollout sau các gate và approval

1. Lưu deploymentID/SHA đang phục vụ và checksum previous assets. Tắt generation qua quy trình cấu hình được duyệt trước khi đổi corpus/receipt. Không nhập scoped receipts vào runtime cũ đang mở generation.
2. Deploy backend đúng SHA; RenderFree, cùng model/embedding,1worker, auto-deployoff. Kế hoạch `ALLOW_STALE_GENERATION=false`, generation vẫnOFF:

   ```bash
   .venv/bin/python scripts/deploy.py backend --commit "$CANDIDATE_GIT_SHA" --receipt reports/deploy-phase2c-NEW.jsonl
   ```

3. CorpusID mới khácproduction: cần stage/restore asset mới bằng operator sau khi testDBrestore và capacity đạt. Restore chỉ corpus/config; backup không chứa source_reviews. Đíchdatabase phải được xác nhận qua metadata, không inconnectionstrings. Với generationOFF và runtime mới đã lên:

   ```bash
   land-law backup --output data/backups/pre-phase2c-NEW.json
   land-law restore dist/phase2c-current-20261021-context-pack/corpus-backup.json
   for receipt in reports/phase2c-current-20261021/receipts-final/*.json; do
     land-law review-source "$receipt"
   done
   land-law activate-source-gate reports/phase2c-current-20261021/source-gate-final.json
   land-law ops-status
   ```

   Các lệnh này sẽ thay production nên CHƯA chạy. Không dùng publish --require-quality=false để mô tả đã đạt quality gate. Chưa hoàn tất source policy, model evaluation, PG hoặc publicE2E thì chưa chứng nhậnready. Không xóa source_gate để làmstatusđạt.
4. `/readyz` và`/api/v1/status` phải khớp GitSHA, PostgreSQL runtime fingerprint trong manifest, corpusID và canonical policySHA. Whole-corpus source_fresh=false vẫn công bố; status scoped usable không tự chứng minh mọi câu hỏi answerable. As-ofscope21/10 phải được giữ/hiển thị đúng; nếu phát hành ngày khác phải review thật, không sửa timestamp để qua gate.
5. Deploy frontend cùng SHA:

   ```bash
   .venv/bin/python scripts/deploy.py frontend --commit "$CANDIDATE_GIT_SHA"
   ```

6. Pilot model và publicE2E cần approval riêng, cùng ngân sách. Turnstile thật→Pages signedingress→Render→SSEfinal→citationPDFđúngtrang; directRender403, mobile/history/error/cooldown. Không tắt Turnstile hoặc nới verifier. Chỉ mở generation khi điều kiện đã được duyệt và evidence thực tế đủ.

## Rollback có thể thực hiện

Trigger: fingerprint/corpus/policy mismatch, citation sai, nguồn thay đổi, lỗi start/ingress hoặc ca demo không hoàn tất.

- Tắt generation trước. Rollback Render vàPages về deployment đã xác minh bằngSHA/deploymentID, giữ asset và policy để điều tra.
- Runtime trướcF01/scoped gate không đủ an toàn để nhận receipts mới: giữ generationOFF, chỉ thư viện, cho tới runtime an toàn được xác minh. Không dùng snapshotoverride.
- Nếu cần corpus cũ, phục hồi backup+receipts tương ứng vào database riêng, xác minh rồi mới chuyển đích qua quy trình được duyệt. Không thử restore/destructive migration trên servingDB, không drop hoặc xóa adverse receipts.
- Không khôi phục server history/messages/answercache hoặc corpus đa dự án. Rollback không có nghĩa cho phép source cũ chưa xác minh phát claim.

SHA production hiện tại và rollback deployment chưa được kiểm controlplane trong Phase2C; bằng chứngPhase2B về deployment cũ không thay kiểm rollout mới.
