# ADR 0006: Standing verified snapshot cho nguồn đã review

**Trạng thái:** Chấp nhận và đã kích hoạt production ngày 22/10/2026 (policy `7e6ec4c4…`, 43 đoạn admitted tại 2026-10-22)

## Bối cảnh

Cơ chế scoped receipt cũ gắn mỗi lần review với cửa sổ ngày ngắn (24 giờ, 72 giờ hoặc tối đa bảy ngày). Khi cửa sổ trôi qua, đoạn văn đã được review và checksum-pinned vẫn bị loại khỏi chat dù nội dung không đổi, receipt không có trạng thái bất lợi và văn bản vẫn còn hiệu lực. Cơ chế quay vòng ngày cũng dễ bị hiểu nhầm là ngày hết hiệu lực pháp lý.

Đồng thời, một ngày review không chứng minh văn bản còn hiệu lực. Cần tách bốn khái niệm: toàn vẹn nội dung, độ mới vận hành, hiệu lực pháp lý tại ngày hỏi và phạm vi điều khoản thực sự được review.

## Quyết định

Dùng policy v2 `standing_verified_snapshot`:

- Giữ nguyên document checksum, passage checksum, SHA256 receipt, `checked_at` và `verified_scope` gốc.
- Ghi `supersedes` là SHA256 của policy v1 đã dùng để migrate; không tự diễn giải lại lịch sử nếu thiếu block này.
- Cửa sổ quay vòng ngày trở thành `standing_chunks`. Tuổi receipt không còn tự động loại đoạn; hiệu lực pháp lý được kiểm tra tại ngày hỏi.
- Cửa sổ dài hơn là phạm vi ngày thực chất của người review, được giữ nguyên trong `legal_windows`; không mở rộng sang ngày khác.
- Receipt mới nhất `changed`/`unavailable`, thiếu receipt, sai checksum hoặc policy lỗi luôn fail closed.
- `source_gate.usable` chỉ mô tả phạm vi đã review; `source_fresh` tiếp tục mô tả toàn corpus. Không tuyên bố snapshot là “pháp luật hiện hành”.
- Kích hoạt bằng operator command, có policy v1 rollback đã lưu và receipt không bị xóa.

## Phương án không chọn

- Không bỏ hoàn toàn source review hoặc đánh dấu toàn corpus đã xác minh.
- Không tự gia hạn `checked_at`, tự tạo receipt mới hoặc quay vòng nguồn theo ngày.
- Không mở rộng 43 đoạn đang dùng thành toàn bộ chunk hoặc toàn bộ receipt lịch sử.
- Không dùng `ALLOW_STALE_GENERATION=true` làm giải pháp thay thế policy.
- Không coi việc policy tồn tại là chứng nhận hiệu lực pháp lý hay chất lượng đáp án.

## Hệ quả

- Cần migration có version, validation và rollback; policy v2 không được sửa tại chỗ.
- Backup corpus không chứa bảng receipt, nên restore vẫn phải nhập lại receipt đã review trước khi mở generation.
- Câu hỏi lịch sử chỉ dùng `legal_windows` đã review; câu hỏi hiện hành dùng `standing_chunks` và vẫn qua `applicability()`.
- Status/API phải hiển thị `review_mode`, `reviewed_at`, `reviewed_as_of`, `operational_expiry` và số đoạn đủ điều kiện.
- Cần regression cho các mốc ngày, văn bản hết hiệu lực, văn bản tương lai, receipt bất lợi, checksum thay đổi, scope không khớp, PostgreSQL, backup/restore và đảo ngược policy.

## Kiểm chứng

`tests/test_standing_source_snapshot.py` kiểm tra migration tất định, đảo ngược, các mốc 2026-10-22/23/25, 2026-11-01, xa hơn bảy ngày, cửa sổ lịch sử, receipt bất lợi, thiếu receipt, checksum thay đổi, đoạn chưa review, văn bản hết hiệu lực và văn bản tương lai. Kết quả fixture không thay thế thẩm định pháp lý hoặc kiểm tra production.
