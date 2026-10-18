# ADR 0002: Lịch sử hội thoại chỉ ở client

**Trạng thái:** Chấp nhận

## Bối cảnh

Ứng dụng công khai không có tài khoản. Nội dung câu hỏi pháp lý có thể chứa thông tin cá nhân; lưu hội thoại trên server làm tăng dữ liệu cần bảo vệ, xóa và khôi phục. Người dùng vẫn cần hỏi tiếp và xem lại nguồn của câu trả lời.

## Quyết định

Lưu hội thoại, đáp án, citation và trace trong IndexedDB theo TTL và giới hạn của frontend. Bearer token API nằm trong `sessionStorage`, tách khỏi lịch sử dài hạn.

Server chỉ giữ metadata xác thực, quota và thực thi. Không lưu messages, answer cache hoặc trace chi tiết giữa các lượt; không replay đáp án. Client gửi history có giới hạn cho từng request và history không được coi là chứng cứ.

## Phương án không chọn

Không lưu lịch sử dài hạn tại backend, không thêm tài khoản hoặc đồng bộ thiết bị. Không chuyển sang server persistence khi IndexedDB lỗi.

## Hệ quả

- Xóa dữ liệu trình duyệt, đổi thiết bị hoặc hết TTL có thể làm mất lịch sử.
- Mất SSE trước kết quả cuối không thể khôi phục đáp án từ server; lượt mới phải do người dùng chủ động gửi.
- Backend vẫn nhận nội dung request và truyền ngữ cảnh cần thiết tới provider; quyết định này không phải cam kết nội dung không rời thiết bị.
- Citation cũ phải được kiểm tra lại; dữ liệu history có thể bị client chỉnh sửa.
- Migration xóa payload cũ và thu hồi quyền runtime; corpus backup không chứa hội thoại.

## Kiểm chứng

Kiểm tra reload, hết hạn, xóa, lỗi storage và giới hạn dữ liệu; kiểm tra history giả không trở thành chứng cứ. Xác minh không có payload trong DB/log/backup khi thành công, lỗi, hủy hoặc timeout. Contract nằm trong [API](../API.md).
