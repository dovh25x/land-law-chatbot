# Release checklist — deployment NOT READY

**PASS** chỉ áp dụng cho phép kiểm được nêu, **FAIL** là không đạt điều kiện đã biết, **NOT TESTED** là chưa có evidence thực thi. Một mục PASS local không đổi mục cloud thành PASS. Candidate chưa commit, push hoặc deploy. Manifest máy đọc: [freeze-manifest.json](freeze-manifest.json).

## Git, phần mềm và image

| Mục | Trạng thái | Evidence/điều còn thiếu |
|---|---|---|
| HEAD nền được nhận diện | PASS | `117e7bd2c4a320c3d02256dfdabf858180b47dbf` và baseline/source hashes |
| Toàn bộ thay đổi trước Phase 4 được giữ | PASS | Kiểm SHA source và 2.906 artifact lịch sử trong [validation](validation.json) |
| Candidate source commit bất biến | FAIL | Working tree dirty; `candidate_commit=null`; không dùng HEAD nền làm SHA đã chứa F01–Phase 3B |
| Backend Python 3.14 | PASS | 516 regression +30 tập con, evidence Phase 3B khớp core source |
| Frontend unit/build/local E2E | PASS |14/ build /100 fixture tests; source không đổi trong Phase 4 |
| Locks/installed packages | PASS local | [Dependency check](dependency-lock-check.json); không tự nâng cấp dependencies |
| Python 3.12/image local | PASS | [Docker checks](docker-preflight.json): image build/probe/memory;516 tests trong testtools layer; giữ 3 lỗi môi trường lần đầu |
| CI trên candidate commit | NOT TESTED | Chưa có commit được duyệt, không trigger workflow |
| Registry image gắn SHA immutable | NOT TESTED | Local image identity có nếu build đạt; chưa push registry/deploy |
| Secret scan cuối và whitespace | PASS | [Scan](secrets-check.log), diff check; chỉ chứng minh phạm vi scanner, không kiểm account settings |

## Database, corpus và receipts

| Mục | Trạng thái | Evidence/điều còn thiếu |
|---|---|---|
| Corpus payload/suite/receipt checksum | PASS | Corpus `corpus-1afca764aa6692e0`; không sửa gold/corpus |
| Scoped source gate ngày 21/10 | PASS local | Source gate usable, checksum-bound receipts; không toàn bộ document fresh |
| Nguồn review phù hợp ngày 23/10/demo | NOT TESTED | Phải kiểm lại đúng scope/date; không tự kéo dài receipt hoặc override F01 |
| Backup/restore corpus SQLite cách ly | PASS | Phase 3B round-trip; thiếu receipt fail-closed rồi reapply usable |
| PostgreSQL local migrations/runtime role/restore | PASS | [PG preflight](postgres-preflight.json); container mới,60 records/7396 chunks, không cloud |
| Upgrade một serving schema cũ và dữ liệu cũ qua migration 006 | NOT TESTED | Local PG dùng schema trống mới; không giả định đã thử nâng cấp production |
| Supabase PG integration trên tuple triển khai | NOT TESTED | Không truy cập remote; cần database thử nghiệm riêng, quyền đúng role |
| Public runtime role không owner/superuser | NOT TESTED cloud | SQL và local role check không chứng minh biến production hiện tại |
| Backup production trước thay đổi, restore vào DB riêng | NOT TESTED | Không được ghi đè serving DB để thử restore; giữ release cũ |
| Model answer final có căn cứ | FAIL điều kiện phát hành | Chưa có model-answer pass trên fingerprint cuối; fixture không thay thế |

Migrations 001–006 được review theo source; migration 006 **xóa server history/cache/trace cũ và thu hồi quyền**, không thể rollback dữ liệu đó. Chỉ chạy migration trên môi trường được phê duyệt và có backup phù hợp; không dùng rollback để phục hồi server history hoặc corpus đa dự án. Không drop database, không gỡ release cũ trước khi release mới và restore đã đạt.

## Ingress, privacy và public E2E

| Mục | Trạng thái | Evidence/điều còn thiếu |
|---|---|---|
| Signed ingress/CORS/Turnstile/quota logic | PASS regression | Tests nguồn hiện tại; không chứng minh cấu hình cloud |
| Signed ingress và allowed origin production khớp | NOT TESTED | Không đọc/đổi secrets hoặc cloud settings trong Phase 4 |
| Turnstile challenge thật/session thực | NOT TESTED candidate mới | Local fixtures không thay challenge thật |
| Provider cooldown/bounded request/budget fail-closed | PASS regression | 30 accounting/reliability tests; không gọi Groq |
| Provider quota live còn đủ | NOT TESTED | 429 TPM đã biết ở Phase 3A; không query quota account mới |
| Allocation cũ đủ cho C02 | FAIL |7.841 còn lại <19.788 required reservation; không reset/refund unknown |
| Server metadata, history browser-only | PASS implementation/regression | Không lưu nội dung chat server; log/retention/account provider thực tế vẫn cần kiểm |
| Provider retention/ZDR được xác minh | NOT TESTED | Không khẳng định xử lý hoàn toàn local hoặc account ZDR |
| Fingerprint/corpus trên public khớp candidate | NOT TESTED | Planned/local PG fingerprint không phải deployed evidence |
| Public navigation, mobile và source panel | NOT TESTED candidate mới | Cần `verify_live_ui.mjs` đúng expected fingerprint sau duyệt |
| Public chat/citation/error recovery end-to-end | NOT TESTED | Cần phê duyệt model/budget; `--chat` hai lượt, không tự chạy |

## Thứ tự release sau khi được phê duyệt

1. Chọn phạm vi được phép phát hành: nếu chưa có evidence model final, giữ generation tắt hoặc source-only theo quyết định chủ dự án; không quảng bá full RAG sẵn sàng.
2. Review và stage **đúng allowlist** trong [code freeze](CODE_FREEZE.md). Kiểm asset corpus bị ignore đã có kênh giao/restore riêng, bìa/tài liệu không chứa secrets. Commit chỉ sau phê duyệt; ghi SHA mới vào manifest release kế tiếp, không sửa manifests lịch sử.
3. CI Python 3.12/frontend/image trên SHA đó; kiểm artifact/image identity. Các source checksums runtime phải khớp freeze. Mọi sửa runtime mới cần quay lại kiểm liên quan, không sửa âm thầm.
4. Tạo backup corpus/config serving được phê duyệt; restore vào DB tách biệt, import receipt theo checksum và kích hoạt đúng policy. Kiểm active corpus, migrations, role, concurrent lease, không messages/trace/cache. Xác minh scope phù hợp ngày hỏi/demo.
5. Sau khi review restore proof và rollback tuple, deploy đúng SHA/image qua quy trình [Operations](../../../docs/OPERATIONS.md), cấu hình cloud đã duyệt. Không truyền owner connection cho runtime, không in secrets.
6. Kiểm readiness, fingerprint/corpus và navigation public; chat chỉ sau duyệt API/budget. Nếu chưa có candidate model pass, không đánh dấu release hoàn tất nhờ health 200.

Workflow hiện có nhận `source_sha` và `verify_public_chat` (mặc định false). Lượt deploy được duyệt trong tương lai phải ghim đầy đủ SHA và giữ chat false nếu chưa có phê duyệt API; không bật quality bypass để gọi deployREADY. Ví dụ chỉ dùng sau review/quyền push/deploy:

```bash
# CHƯA THỰC THI: cần repository/branch/source SHA đã duyệt và CI tương ứng.
gh workflow run deploy.yml --ref '<branch-da-duyet>' \
  -f source_sha='<full-40-character-reviewed-commit>' -f verify_public_chat=false
```

## Rollback có thể thực hiện

Tuple cần ghi trước deploy: `(source commit, immutable image, corpus payload SHA, policy SHA, receipt bundle SHA, PG migration compatibility, runtime fingerprint)`. Hiện **chưa có tuple cloud known-good đầy đủ cho candidate này**, vì vậy không hứa đã thử rollback production.

Nếu public smoke fail sau deploy: ngừng generation qua cấu hình được duyệt, giữ source lookup nếu còn đúng corpus; quay về image/source tuple đã xác minh tương thích schema và privacy. Giữ database/release cũ; restore corpus/config vào DB mới để xác minh trước khi chuyển serving, import receipts riêng vì backup không mang source_reviews. Không `DROP DATABASE`, không restore đè, không rollback migration 006 để ghi server history. Nếu không có tuple tương thích, giữ generation ngừng và công bố giới hạn; đó là phương án an toàn, không phải rollbackPASS.

Kết luận: local preflight có thể giảm blocker kỹ thuật, nhưng thiếu model evidence, commit/CI/cloud/dated scope/public E2E vẫn khiến **deployment NOT READY**. Không có lệnh triển khai nào được thực thi trong Phase 4.
