# ADR 0005: Phạm vi một dự án và thu hồi corpus cũ

**Trạng thái:** Chấp nhận

## Bối cảnh

Sản phẩm chỉ phục vụ Vành đai 4. Giữ dữ liệu của các dự án khác trong corpus vận hành làm tăng khả năng truy xuất sai phạm vi và khiến giao diện, cấu hình cùng quy trình phát hành phức tạp hơn mức cần thiết.

## Quyết định

Chỉ vận hành và phát hành nguồn Vành đai 4 cùng luật, quy định chung liên quan. Xóa nguồn dự án không hỗ trợ khỏi manifest, danh mục, raw/cache/checkpoint và corpus vận hành; giữ các câu hỏi ngoài phạm vi trong bộ đánh giá.

Tạo corpus ID mới khi thay đổi phạm vi, tái sử dụng embedding của chunk giữ lại và kiểm tra lại quan hệ/tham chiếu. Chỉ gỡ asset corpus cũ sau khi bản mới đã phát hành, tải được, restore riêng thành công và chuyển active.

## Phương án không chọn

Không giữ nguồn dự án khác chỉ để phục vụ ca đánh giá ngoài phạm vi. Không embedding lại toàn bộ corpus khi chỉ lọc dữ liệu. Không viết lại Git hoặc sửa checksum báo cáo cũ để che thay đổi phạm vi.

## Hệ quả

- Tin dự án và luật chung phải được phân loại theo vai trò chứng cứ; nhãn dự án không phải tiêu chí duy nhất để loại luật chung cần thiết.
- Các tham chiếu, coverage gaps và gold cần được kiểm tra toàn vẹn sau chuyển đổi.
- Báo cáo lịch sử được giữ nhưng có thể không tái lập đầy đủ sau khi asset nguồn bị thu hồi; bản ghi thu hồi phải công khai giới hạn này.
- Rollback chỉ được dùng corpus một dự án và code không lưu hội thoại. Nếu chưa có phiên bản phù hợp, tắt generation và giữ nguồn.

## Kiểm chứng

Đối chiếu checksum, corpus ID, source commit, phạm vi tài liệu, chunk và tham chiếu; restore vào SQLite/PostgreSQL riêng trước chuyển active. Quy trình nằm trong [vận hành](../OPERATIONS.md); bằng chứng thu hồi nằm trong [artifact](../../reports/corpus-retirement.json).
