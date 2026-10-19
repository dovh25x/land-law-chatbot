# Kiểm tra điều kiện phát hành corpus

**Chưa đủ điều kiện phát hành/deploy.** Đây là bằng chứng kỹ thuật có phiên bản, không phải chứng nhận pháp lý độc lập. Không sửa database phục vụ, không publish Release và không deploy production trong các bước đã ghi nhận.

Corpus ứng viên `corpus-a26bc99e541fbbe2` gồm 60 văn bản, 7.392 chunks. Giữ nguyên toàn bộ 7.388 vectors từ ứng viên trước, chỉ embedding bốn chunks của QĐ20/2022 mới được đối chiếu hai trang PDF gốc. Không thay model, embedding contract hoặc hosting. Candidate, backup và package nằm trong `data/staging/readiness-20261019-attempt-1/` (không theo dõi Git); chúng chưa phải asset phát hành.

Bản runtime cho lượt kiểm tra mới nhất: `6ca8f12f0d770f2076de20f0d070460894bd0bc8`, fingerprint PostgreSQL `380801c7436b04ac3535585b949a937656bec603fa6db3197f313bcd8cb9401c`. [Runtime/hashes](runtime-attempt-6.json), [software evidence cuối](software-checks-release-final.json), [toàn bộ hồi quy backend](backend-tests-claim-conditions.log). Các file `runtime-final-source.json`, `software-checks.json`, `software-checks-final.json` và các bản software trước đó là bằng chứng lịch sử, không phải bản cuối.

## Bằng chứng đã hoàn tất

- Backend: 248 tests đạt. [Ca hồi quy trước sửa repair](repair-context-regression-before.log) tái hiện `KeyError: previous_draft`. [Hồi quy claim trước sửa](claim-conditions-regression-before-2.log): ba trường hợp sai vẫn lọt qua verifier duyệt tất cả; ba đối chứng đúng đạt. Bản sửa chặn mất hợp đồng, chủ thể bị khái quát và phụ thuộc “các quy định trên”; không nối thêm điều kiện sau verify. Frontend: 5 unit tests, build và 68 E2E đạt; [source frontend không đổi](frontend-source-parity.json) sau các lượt này. [Secret scan cuối](secrets-after-diagnostics.log) đạt.
- [Hồi quy no-drop trước sửa](no-drop-regression-before.log): sáu đường lỗi vẫn gọi DROP. Bản sửa `f0fabae` giữ database và đóng kết nối ở cả lỗi migration/validation. [Receipt](generation-postgresql-attempt-5/isolated-databases.jsonl) và [truy vấn catalog sau lượt chạy](retained-database-verification.json) xác nhận database riêng được giữ lại. Các báo cáo restore trước thay đổi quy tắc này giữ nguyên mô tả lịch sử; không đổi thành bằng chứng retention.
- [Parser/chunk integrity](corpus-integrity.json): đối chiếu lại 60/60 nguồn trong candidate, không lỗi/cảnh báo kỹ thuật. Không thay thế kiểm tra OCR/pháp lý.
- [Restore SQLite](restore-and-retrieval-attempt-1/sqlite/restore-and-retrieval.json) và [PostgreSQL](restore-and-retrieval-attempt-1/postgresql/restore-and-retrieval.json): khớp candidate, không chứa conversation history. Raw retrieval trên từng backend: smoke 10/11, supplemental 3/3, natural 0,9167. Không sửa gold để làm đẹp số liệu; retrieval hit không chứng minh answer đúng.
- [Role/privacy PostgreSQL](postgres-runtime-role.json): kiểm tra trên database tạm riêng, không viết history, giữ lease phiên đúng.
- [QĐ20/2022](qd20-2022-review.json): đối chiếu cả hai trang PDF Chính phủ, ghi đúng phạm vi sửa khoản 2 Điều 26 QĐ10 và quan hệ bãi bỏ bởi QĐ27. Chưa hoàn tất dependency QĐ10/Điều 7 và chưa tạo freshness receipt.
- [Package local](package-preparation.json): kiểm tra schema/chunk hashes/secrets và chuẩn bị asset, chưa upload/download GitHub Release. Không tính package local là bước download/restore Release đã đạt.
- [Probe key do người dùng cập nhật](updated-key-probe.json): một request HTTP 200, token bucket trả về 8.000 token/phút; không chứng minh toàn bộ bộ đánh giá hay quota ngày đã đạt.

## Lịch sử đánh giá model

Giữ bộ smoke 20 + supplemental 4 + natural 8 đã khóa; checksum nằm trong [plan](plan.json). Không chọn kết quả đẹp giữa các runtime hoặc gộp bộ chưa hoàn thành để tuyên bố đạt.

| Lượt | Phạm vi | Tình trạng |
|---|---|---|
| `generation-attempt-1` | SQLite, candidate trước | 8 natural, runtime lịch sử; không đại diện runtime cuối |
| `generation-postgresql-attempt-1` | PostgreSQL | Dừng sau 3 smoke để sửa lỗi; giữ nguyên partial artifact |
| `generation-postgresql-attempt-2` | PostgreSQL | Natural 8, smoke 5; có thay source lúc process đang giữ module cũ, không hợp lệ cho acceptance; xem [giải trình](postgresql-attempt-2-interrupted.json) |
| `generation-postgresql-attempt-3` | PostgreSQL, runtime `0e4c4dd` | Natural 8: 3 pass, 2 partial, 3 fail; smoke 14/20: 10 pass, 2 partial, 2 fail (S14 limited TPD). Supplemental chưa chạy. Không đạt |
| `generation-postgresql-attempt-4` | PostgreSQL, runtime `8ebdc35` | Đủ 32/32, 31 requests, không limited/error. Smoke: 18 pass, 1 partial, 1 fail; supplemental: 2 pass, 2 fail; natural: 5 pass, 1 partial, 2 fail, trong đó nội dung 3/6 đạt. Không đạt |
| `generation-postgresql-attempt-5` | PostgreSQL, runtime `4d0fd9f`; resume helper `f0fabae`, cùng fingerprint `8db2d701…` | Đã thực thi đủ 32 ca; còn 1 limited ở S17. Smoke: 16 pass, 2 partial, 2 fail; supplemental: 2 pass, 2 fail; natural: 4 pass, 1 partial, 3 fail, trong đó nội dung chỉ 2/6 đạt. Giữ 34 attempt, gồm các lần bị quota trước resume. Không đạt |
| `generation-postgresql-attempt-6` | PostgreSQL, runtime `6ca8f12` | N02 thực thi xong với 2 LLM requests, không limited/error nhưng review vẫn fail. Chỉ 1/8 ca natural; không phải bộ 32 ca trên fingerprint mới |

[Rà soát lượt 3](reviewed-postgresql-attempt-3/natural/results.md) gắn checksum từng answer. N02 khái quát thiếu điều kiện; N03 mới nêu định nghĩa người trực tiếp sản xuất mà thiếu điều kiện đất/hình thức hỗ trợ; N04/N05 không trả lời được; N06 thiếu lưu ý hồ sơ cũ. Smoke S04 thiếu quy định chậm chi trả theo rubric, S06 không phân biệt được Điều 95, S08 thiếu điều kiện riêng. Các ca chưa có câu trả lời đạt không được tính pass chỉ vì verifier đã chặn nội dung sai.

Helper hiện khóa fingerprint trước mỗi provider call và mỗi split. Source/config khác cần thư mục mới; limited/error có thể resume nhưng mọi attempt được giữ. `--no-generation` chặn provider và giữ cooldown, không thay thế lượt model.

[Lượt 4](generation-attempt-4-completion.json) xác nhận key mới chạy được đầy đủ bộ khóa. [Review](reviewed-postgresql-attempt-4/natural/results.md) vẫn giữ lỗi N02/N04 và partial N06; không suy chất lượng từ HTTP 200 hoặc từ status `answered`. [Đính chính locator review lượt 3](review-attempt-3-erratum.json) chỉ sửa nhận định về số khoản trong lời bình, không đổi answer hay verdict lịch sử.

[Lượt 5](generation-attempt-5-completion.json) giữ mọi attempt: trần quan sát là 6 LLM requests, 12 tools và 45.772 ms một lượt. [Natural review](reviewed-postgresql-attempt-5/natural/results.md), [smoke review](reviewed-postgresql-attempt-5/smoke/results.md), [supplemental review](reviewed-postgresql-attempt-5/supplemental/results.md) gắn checksum answer. N02 có cả thiếu hợp đồng/chủ thể sai và suy áp dụng từ hiệu lực; N03 bị verifier nhầm khoản 2 với khoản 4 được dẫn chiếu; N04 vẫn không trả lời trọng tâm; N06 chưa đủ lưu ý hồ sơ cũ. Repair có đủ đầu vào không đồng nghĩa model sửa đúng.

[Lượt 6](reviewed-postgresql-attempt-6/natural/results.md) vẫn diễn giải địa bàn thành nơi có quyết định phê duyệt thay vì nơi có đất thu hồi tại thời điểm phê duyệt, đồng thời chưa phân biệt đủ các nhánh Điều 19. Không tính status `answered` là pass. [Replay offline](actual-answer-guard-replay.json) xác nhận nguyên văn các claim sai của lượt 5 bị guard mới chặn cả ba lỗi mà không gọi model; đây là bằng chứng chặn lỗi cũ, không phải chứng minh mọi câu trả lời mới đúng.

Key mới vẫn chịu giới hạn thực tế: log lượt 5 ghi TPM 8.000 và TPD 200.000; lúc bị chặn ngày, provider báo used 198.768/requested 2.332. Resume sau cooldown chỉ chạy limited/error hoặc ca chưa thực thi. [Bằng chứng phase resume](generation-attempt-5-resume-phase.json) xác nhận helper retention thay đổi nhưng core fingerprint không đổi; các ca natural đã hoàn tất không chạy lại. Log quota trùng ở một số split là hai observer nhận cùng response, không phải hai request mới; số request lấy từ budget/attempt.

## Phần còn chặn phát hành

[Danh sách nguồn cần duyệt](source-review-worklist.json) ghi bảy nguồn pending với tổng 482 trang PDF và một ứng viên sửa đổi mới bảy trang. Chưa duyệt đủ OCR, điều kiện, dẫn chiếu, hiệu lực/chuyển tiếp; không đánh dấu verified hàng loạt. [Kiểm tra trực quan NQ106](nq106-ocr-spot-check.json) xác nhận OCR sai ngày 18 thành 48 ngay trang đầu; không thể lấy confidence/hash thay duyệt nguồn.

[Ứng viên NĐ281/2026](nd281-source-candidate.json) được tải/OCR riêng, chưa nhập corpus. Đã đọc trực quan cả bảy trang và lập [bản đồ điều khoản](nd281-article-scope-review.json), bao gồm sửa/bổ sung, bãi bỏ cụm từ/phạm vi và điều khoản chuyển tiếp. Bản đồ này không chứng nhận toàn văn OCR hoặc giải quyết thay người rà soát các điểm tác động chồng lấn. Phải đối chiếu NĐ123/2024 trước khi phục vụ. Không suy rằng toàn bộ nghị định gốc bị bãi bỏ. Không tạo freshness receipt từ việc tải được URL hoặc hash toàn văn không đổi.

Cổng deploy kiểm tra lại manifest gắn SHA-256 của candidate/backup, coverage/dependency, freshness, review đầy đủ bộ khóa đúng fingerprint PostgreSQL, software, restore hai backend, role/privacy và asset Release đã download. SHA deploy là SHA đã kiểm thử. Commit bằng chứng chỉ được khác tài liệu/báo cáo; thay source/data/CI bắt buộc kiểm thử lại.

[Trạng thái production đọc riêng mới](production-readonly-status-resume-2.json) tại `/api/v1/status` ghi corpus cũ `corpus-581da76c79b0b362`, HTTP 200 nhưng generation bị chặn `source_stale`. Lần thử `production-readonly-status-resume.json` dùng sai đường `/api/status` và timeout, không được dùng làm bằng chứng status. Chỉ publish/promote/deploy sau khi các cổng thật sự đạt; không giảm ngưỡng, ghép N02 của lượt 6 vào lượt 5, hoặc chuyển artifact lịch sử thành kết quả runtime hiện tại.

Phần còn phải hoàn thành: duyệt nguồn/chuỗi sửa đổi và chuyển tiếp, tạo receipt freshness thật, thẩm định nội dung pháp lý, đạt trọn bộ khóa trên fingerprint dùng phát hành, tải/restore asset Release thật, rồi mới deploy SHA đã kiểm thử và đối chiếu corpus/fingerprint phục vụ. Không xóa corpus cũ hoặc embedding lại toàn bộ để che các lỗi điều kiện/kiểm chứng đã tìm thấy.

[Cổng phát hành được tính lại](readiness-final.json) dùng [manifest gắn checksum](readiness-inputs-final.json). Ba review full-suite tham chiếu cùng cohort lượt 5 và bị loại vì không khớp fingerprint runtime cuối; chẩn đoán N02 của lượt 6 chỉ là input tham khảo, không được ghép vào cohort cũ để tính pass. Chưa có bằng chứng full-suite đạt trên runtime cuối, coverage/dependency chưa đầy đủ, nguồn chưa fresh và chưa có asset Release đã download/restore. Báo cáo blocked không cho phép deploy.

`ready=false`: `coverage`, `source_freshness`, ba cổng `generation` và `release_download` đều chặn. Revision đã kiểm thử, backup khớp candidate, restore hai backend, software và role/privacy đạt. [Preflight deploy](deployment-preflight-final.json) kiểm tra hai entrypoint production với HTTP và process deploy bị chặn trong diagnostic; báo cáo từ chối không được dẫn đến thao tác bên ngoài.

[Danh sách SHA-256](ARTIFACT_SHA256SUMS) ràng buộc toàn bộ file báo cáo ở thời điểm chốt, trừ chính file danh sách. Candidate/backup local có checksum riêng trong manifest; không xem đường dẫn staging chưa có trong checkout CI là asset đã phát hành.
