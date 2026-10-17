# Lịch sử phía client

Trạng thái: chấp nhận.

## Quyết định

IndexedDB giữ history/citation/trace 7 ngày; server chỉ metadata và không replay đáp án.

## Lý do và hệ quả

Giảm dữ liệu cá nhân phía server, nhưng xóa browser hoặc mất SSE có thể làm mất nội dung. Không đồng bộ thiết bị. Client history không là bằng chứng; mỗi lượt truy xuất lại.
