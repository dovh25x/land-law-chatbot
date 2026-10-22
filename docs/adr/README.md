# Architecture Decision Records

ADR ghi lại các quyết định có ảnh hưởng lâu dài tới kiến trúc và vận hành. Mỗi bản nêu bối cảnh, lựa chọn, phương án không chọn và hệ quả. Trạng thái “chấp nhận” biểu thị quyết định được sử dụng, không phải chứng nhận chất lượng hoặc availability.

| ADR | Quyết định | Trạng thái |
|---|---|---|
| [0001](0001-pipeline.md) | Một pipeline và contract embedding cố định | Chấp nhận |
| [0002](0002-client-history.md) | Lịch sử chỉ ở client, server không replay đáp án | Chấp nhận |
| [0003](0003-ingress-quota.md) | Ingress có chữ ký và tách quota public/operator | Chấp nhận |
| [0004](0004-evidence.md) | Kết luận giới hạn bởi chứng cứ | Chấp nhận |
| [0005](0005-corpus-scope.md) | Một dự án và quy trình thu hồi corpus | Chấp nhận |
| [0006](0006-standing-source-snapshot.md) | Standing verified snapshot thay cho hạn vận hành ngắn | Chấp nhận cho implementation; chờ duyệt production |

Chỉ thêm hoặc thay thế ADR khi quyết định kiến trúc thay đổi. Không dùng ADR làm nhật ký bàn giao, danh sách tác vụ hoặc nơi sao chép kết quả benchmark. Nếu một quyết định bị thay thế, liên kết tới bản thay thế và giữ bối cảnh của quyết định cũ.
