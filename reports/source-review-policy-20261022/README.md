# Đề xuất chính sách rà soát nguồn 72 giờ — 2026-10-22

**Trạng thái:** Đề xuất, **chưa được phê duyệt và chưa áp dụng**. Production vẫn dùng cửa sổ 24 giờ hiện hành. Không có receipt, database, Render hay Cloudflare nào bị thay đổi bởi tài liệu này.

## Chính sách đang có hiệu lực

| Thuộc tính | Giá trị |
| --- | --- |
| Gate policy SHA256 | `015e33634ae920889271bbfcdf1a3e20977116b21c6c10be4face0c962d8d220` |
| Số đoạn hợp lệ hôm nay | 43 |
| Ngày hiệu lực của câu hỏi | `2026-10-22` (`Asia/Ho_Chi_Minh`) |
| Hết hạn kế tiếp | `2026-10-23 00:00 Asia/Bangkok` = `2026-10-22 17:00 UTC` |
| Sau hết hạn | Còn 1 đoạn hợp lệ từ cửa sổ dài; ngày `2026-10-28` còn 0 đoạn |
| Cấu hình freshness | `ALLOW_STALE_GENERATION=false` |

Đây là mốc vận hành bắt buộc. Chính sách 72 giờ chỉ thay thế sau khi có candidate được review, replay và phê duyệt trước mốc trên.

## Thay đổi đề xuất

Một scope rà soát mới được phép dài tối đa **72 giờ** (ba ngày lịch, end exclusive), không tự động gia hạn. Candidate minh hoạ:

| Trường | Giá trị |
| --- | --- |
| `as_of_from` | `2026-10-23` |
| `as_of_to` | `2026-10-26` (exclusive) |
| Hết hạn | `2026-10-26 00:00 Asia/Bangkok` |
| Điều kiện bắt đầu | Recheck + legal applicability review + replay + approval trước `2026-10-23 00:00` |

Candidate này **chưa được tạo** vì chưa có vòng re-fetch và review pháp lý mới. Không dùng lại `checked_at`, `review_evidence` hoặc kết luận review của cửa sổ 24 giờ để giả định hiệu lực 72 giờ.

## Điều kiện pháp lý và an toàn trước khi áp dụng

1. **Re-fetch toàn bộ nguồn ghim.** Chạy lại `reports/source-review-20261022/recheck_sources.py` (hoặc quy trình tương đương) cho 10 tài liệu/28 artifact chính thức; mọi checksum byte hoặc text phải khớp bản đã review. Có bất kỳ lỗi nào thì dừng.
2. **Kiểm tra hiệu lực và applicability.** Người review xác nhận:
   - không có văn bản sửa đổi, thay thế hoặc hướng dẫn mới làm đổi nội dung/hiệu lực của các đoạn được ghim;
   - từng đoạn có hiệu lực trong suốt `2026-10-23` → `2026-10-25`;
   - quan hệ pháp lý, ngày hiệu lực và phạm vi Vành đai 4 không đổi;
   - đoạn nào không chắc chắn bị loại khỏi scope mới.
3. **Append-only.** Chỉ thêm scope mới vào receipt; giữ nguyên scope cũ, chunk checksum, text, `review_evidence` cũ và lịch sử. Không sửa file lịch sử để khớp chính sách mới.
4. **Replay offline.** Gate phải usable tại `2026-10-23`, `2026-10-24`, `2026-10-25` và fail closed tại `2026-10-26`; kiểm tra cả câu hỏi lịch sử và scope 24 giờ cũ.
5. **Phê duyệt.** Candidate policy phải có SHA256 và biên bản review. Chỉ sau đó mới ghi receipt bổ sung và cập nhật con trỏ gate.
6. **Không bật `ALLOW_STALE_GENERATION`.** Cửa sổ 72 giờ không thay thế scoped receipt gate, không xác minh toàn corpus và không mở quyền cho đoạn ngoài scope.

## Kiểm thử hết hạn

Test biên nằm tại `tests/test_source_review_window_policy.py`:

```bash
.venv/bin/python -m pytest -q tests/test_source_review_window_policy.py
```

Kỳ vọng: scope `2026-10-22` → `2026-10-25` usable trong các ngày `2026-10-22`, `2026-10-23`, `2026-10-24`; tại `2026-10-25` và sau đó gate trả `eligible_passages=0`, `usable=false`. Đây là kiểm thử semantics của gate, không phải phê duyệt chính sách.

## Bằng chứng được giữ và rollback

- Policy 24 giờ hiện hành: `reports/source-review-20261022/source-gate-20261022.json` (SHA `015e…`).
- Receipt 24 giờ và scope lịch sử: `reports/source-review-20261022/receipts-20261022/` và các receipt đã ghi trong database.
- Khi áp dụng candidate, con trỏ `source_gate:corpus-1afca764aa6692e0` chỉ được đổi sau replay thành công; receipt mới là additive.
- Rollback: dùng operator CLI `land-law activate-source-gate reports/source-review-20261022/source-gate-20261022.json` với đúng `ADMIN_DATABASE_URL`, sau khi xác nhận database đích và receipt cũ còn nguyên. Không drop database, không sửa corpus.
- Nếu chưa kiểm chứng rollback hoặc candidate không đạt: giữ 24 giờ; nếu không kịp quay vòng trước hạn, tắt generation (`GENERATION_ENABLED=false`) và giữ tra cứu nguồn thay vì coi 1 đoạn còn lại là đủ.

## Quyết định cần có

- Chấp thuận hay từ chối trần 72 giờ và candidate `2026-10-23` → `2026-10-26`.
- Chỉ định người review pháp lý chịu trách nhiệm xác nhận applicability.
- Phê duyệt SHA của candidate sau khi recheck/replay; nếu không kịp trước `2026-10-23 00:00 Asia/Bangkok`, thực hiện vòng 24 giờ hoặc tắt generation theo fallback ở trên.
