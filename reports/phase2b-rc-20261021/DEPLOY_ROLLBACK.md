# Deploy và rollback — kế hoạch chưa thực thi

**NOT READY.** Phase 2B chưa commit, push, migrate production, đổi cấu hình production, publish Release hoặc deploy.

## Điều kiện trước khi phát hành

1. Người dùng duyệt changeset và phạm vi hỗ trợ. Cần review thêm các chủ đề hiện hành tối thiểu, hoặc thống nhất công khai một MVP chỉ tra cứu các mốc lịch sử đã duyệt. Coverage của suite lịch sử không chứng minh coverage hiện hành.
2. Kiểm chứng PostgreSQL riêng. Môi trường này chưa có `postgres`, `initdb` hoặc Docker WSL dùng được. Chưa xác minh migration, role, restore và retrieval trên PostgreSQL. Các helper có `--postgres` tạo database trên instance được cấu hình; chưa chạy trong vòng này.
3. Kiểm tra migration ledger trước mọi thao tác production. Migration `006_browser_history.sql` xóa payload hội thoại; không chạy lại trên serving database như phép thử. Runtime phải đọc được `source_reviews` và policy trong `app_state`, chỉ được ghi state cho cooldown.
4. Pilot model trên cấu hình cuối và public E2E chưa chạy. S06 vẫn FAIL ở attempt cũ; không tuning hoặc gọi lại. `check_release_readiness.py` vẫn giữ các gate toàn corpus, coverage và model evidence; chưa đạt và không được đổi threshold để tạo kết quả pass.
5. Xác minh rollback deployment và asset còn truy cập được. SHA production có bằng chứng lịch sử là `d2424ed5469df05d0994b56daa02d4765323ae83`; GET hiện tại chỉ xác nhận fingerprint cũ, chưa xác nhận SHA qua control plane.

## Commit và freeze sau review

Các lệnh sau là hướng dẫn, chưa thực thi:

```bash
git diff --check
git switch -c phase2b/legal-source-gate-rc
# Chỉ stage danh sách đã duyệt trong CHANGESET.md, không dùng git add .
git add --pathspec-from-file=reports/phase2b-rc-20261021/reviewed-paths.txt
git commit -m "Gate legal claims on reviewed passages and prepare scoped candidate"
git rev-parse HEAD
# Chỉ khi có phép push:
git push -u origin phase2b/legal-source-gate-rc
```

Ghim SHA thực tế gồm 40 ký tự. `117e7bd` hiện chỉ là base commit, chưa chứa patch. So khớp source-tree hashes, chạy lại checks nếu code/config thay đổi và đóng gói vào thư mục mới mang SHA. Không ghi đè manifest hoặc artifact cũ.

## PostgreSQL thử nghiệm và backup

Sau khi được duyệt quyền tạo test database, dùng helper có sẵn:

```bash
.venv/bin/python scripts/verify_postgres_database.py --source <candidate-backup> --output <new-report>
```

Helper tạo database riêng, áp dụng migrations và kiểm corpus, runtime role, session lease, quyền ghi history. Helper này chưa nhập scoped receipts: phải nhập bộ receipt/policy vào chính test database, kiểm quyền đọc với runtime role và kiểm việc ghi policy bị chặn bằng transaction rollback. Giữ database/receipt; không tự drop hoặc dọn Release cũ.

Asset local ở `dist/phase2b-rc-20261021/`. Corpus backup, manifest đóng gói và source-review ZIP đều được bind bằng checksum trong release manifest. Chưa upload/download qua GitHub Release. Restore SQLite đã kiểm exact corpus và fail-closed khi thiếu receipt; chưa có bằng chứng tương đương trên PostgreSQL.

Trước thay đổi production, backup corpus/config và lưu các source-review receipts mới nhất riêng. Không backup messages, traces hoặc answer cache. Thử restore vào database riêng trước khi sử dụng để phục hồi.

## Rollout theo SHA sau approval

1. Lưu metadata deployment trước, previous Release và checksum asset. Xác minh rollback còn dùng được. Tạm tắt public generation bằng `GENERATION_ENABLED=false` qua quy trình cấu hình được duyệt; không nhập receipt vào runtime cũ khi generation còn mở.
2. Deploy backend đúng RC SHA, Render Free, auto-deploy off, một worker. Cấu hình kế hoạch `ALLOW_STALE_GENERATION=false`; giữ model, embedding, hosting và secrets:

   ```bash
   .venv/bin/python scripts/deploy.py backend --commit <RC_SHA> --receipt <new-jsonl>
   ```

3. Corpus ID đang khớp nên không cần restore hoặc publish lại toàn corpus vào serving DB. Operator xác nhận database đích/checksum, nhập bảy receipts bằng `land-law review-source <file>`, rồi `land-law activate-source-gate <source-gate.json>`. Receipt hết hạn hoặc checksum khác phải dừng để review, không sửa `checked_at` cho qua. Runtime role không thực hiện bước này.
4. `/readyz` phải phản ánh đúng PostgreSQL, corpus, runtime fingerprint và canonical policy hash. `/api/v1/status` phải báo policy usable và đúng số đoạn được duyệt. `source_fresh=false` của toàn corpus vẫn phải được công bố. Không chỉ kiểm HTTP 200.
5. Deploy frontend cùng SHA:

   ```bash
   .venv/bin/python scripts/deploy.py frontend --commit <RC_SHA>
   ```

   Giữ same-origin Pages và signed ingress. Chỉ mở generation sau các kiểm tra được duyệt.
6. Public E2E dùng Turnstile thật và câu hỏi giả lập: tạo phiên, HMAC qua Pages, SSE đến result cuối, citation đúng PDF/page, mobile/history/error/cooldown. Kiểm direct Render trả 403. Mọi test có khả năng gọi Groq cần approval riêng và phải trừ vào ngân sách evaluation chung; không tắt Turnstile hoặc dùng test key để đạt.
7. Lưu SHA, fingerprint, policy/corpus hash và kết quả thực tế. Không chứng nhận quality-ready chỉ từ liveness. Chỉ gỡ Release cũ sau khi bản mới hoạt động và restore đạt.

## Rollback fail-closed

- Trigger: SHA/fingerprint/policy khác manifest, health không ổn định, citation/source gate vi phạm hoặc demo không hoàn tất.
- Tắt public generation trước; rollback về deployment Render và Pages đã xác minh, giữ asset cũ. Không phục hồi server history hoặc corpus đa dự án.
- Không thử restore trên serving DB. Nếu cần phục hồi corpus, restore asset sang DB riêng, kiểm scope/checksum/receipts rồi mới đổi đích qua quy trình được duyệt.
- Runtime trước Phase 1 có thể không hiểu scoped receipts và còn lỗi F01. Rollback về runtime đó phải **giữ generation OFF**, chỉ mở thư viện. Không bật snapshot override để demo. Hiện chưa có bản đã deploy chứa cổng mới để rollback về.
- Giữ policy, adverse receipts và mọi attempt. Restore thiếu receipt phải tiếp tục từ chối; không xóa policy để làm status đạt.
