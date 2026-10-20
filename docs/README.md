# Tài liệu kỹ thuật

Tài liệu mô tả phạm vi sản phẩm, thiết kế và cách vận hành Hanoi Land Law Assistant. Các kết quả đo và xác minh thuộc từng phiên bản được lưu trong `reports/`; tài liệu thiết kế không thay thế bằng chứng thực thi.

## Lộ trình đọc

| Nhu cầu | Tài liệu |
|---|---|
| Cài đặt và chạy ứng dụng | [README](../README.md) |
| Hiểu vấn đề, người dùng và phạm vi | [PRD](PRD.md) |
| Đọc thiết kế đích cho người dân và lộ trình triển khai | [Thiết kế lại v2](redesign/README.md) · [trạng thái triển khai](redesign/IMPLEMENTATION.md) |
| Đọc luồng xử lý và ranh giới tin cậy | [Kiến trúc](ARCHITECTURE.md) |
| Phản biện thiết kế và xem agent flow | [Agent flow](AGENT_FLOW.md) |
| Tích hợp phiên, chat và SSE | [API](API.md) |
| Phát triển giao diện theo Figma | [Frontend](FRONTEND.md) |
| Triển khai, xử lý sự cố và khôi phục | [Vận hành](OPERATIONS.md) |
| Đối chiếu đợt phát hành cho người dân | [Bằng chứng ban đầu](../reports/production-readiness-20261020/README.md) · [đợt hoàn thiện tiếp theo](../reports/production-finalization-20261020/README.md) |
| Chạy và diễn giải đánh giá | [Đánh giá](EVALUATION.md) |
| Hiểu các lựa chọn kiến trúc | [ADR](adr/README.md) |
| Chỉnh sửa hoặc xuất lại sơ đồ | [Nguồn diagram](diagrams/README.md) |

## Quy ước tài liệu

- README là điểm bắt đầu; mỗi tài liệu chuyên đề chịu trách nhiệm cho một chủ đề, dùng liên kết thay vì sao chép nội dung.
- PRD mô tả hành vi cần đạt. Kiến trúc và API mô tả implementation; khác biệt hoặc giới hạn đã biết phải được ghi rõ.
- ADR lưu bối cảnh, lựa chọn và hệ quả của quyết định. Trạng thái “chấp nhận” không có nghĩa mọi tiêu chí chất lượng đã đạt.
- `reports/` chứa kết quả, checksum, cấu hình và phạm vi kiểm chứng của từng lần chạy. Không cập nhật số liệu bằng cách sửa tài liệu thiết kế.
- Ví dụ cấu hình không chứa credentials. `.env.example` liệt kê tên biến; secret được quản lý ngoài Git.

Khi thay đổi subsystem, cập nhật tài liệu sở hữu contract đó và ADR nếu quyết định kiến trúc thay đổi. Không viết lại artifact lịch sử để khiến kết quả cũ có vẻ khớp phiên bản mới.
