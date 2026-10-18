# Yêu cầu sản phẩm

## Bài toán

Người tra cứu cần xác định quy định liên quan tới bồi thường, hỗ trợ và tái định cư, điều kiện áp dụng và nguồn để đối chiếu. Văn bản có thể được sửa đổi hoặc thay thế; thông tin tổng quan dự án không đủ để xác nhận quyền lợi của từng hộ.

Hanoi Land Law Assistant hỗ trợ quá trình tìm và đọc nguồn cho Vành đai 4 tại Hà Nội. Sản phẩm cung cấp thông tin có dẫn chứng và công khai giới hạn khi thiếu dữ kiện hoặc chứng cứ.

## Người dùng và tác vụ

| Người dùng | Tác vụ chính |
|---|---|
| Người tra cứu | Hỏi quy định, làm rõ điều kiện và mở nguồn để đối chiếu |
| Người đọc văn bản | Tìm số hiệu, xem điều khoản, thời điểm và quan hệ thay thế |
| Người vận hành | Kiểm tra corpus, usage, trạng thái dịch vụ và tính phù hợp của báo cáo |

Ứng dụng công khai, không yêu cầu tài khoản. Lịch sử thuộc thiết bị sử dụng, không phải hồ sơ được lưu trữ hoặc đồng bộ bởi dịch vụ.

## Phạm vi chức năng

| Khả năng | Hành vi yêu cầu |
|---|---|
| Hỏi đáp | Nhận câu hỏi tiếng Việt; trả nội dung được kiểm chứng, hỏi làm rõ hoặc nêu chưa đủ chứng cứ |
| Hỏi tiếp | Dùng ngữ cảnh hội thoại để giải tham chiếu; truy xuất và kiểm chứng lại kết luận mới |
| Citation | Mở văn bản nguồn, locator, trang nếu có và đoạn trích tương ứng |
| Trace | Hiển thị bước thực thi và nguồn đã dùng; không hiển thị suy nghĩ nội bộ |
| Lịch sử | Xem lại, xóa từng cuộc, xóa toàn bộ và tự hết hạn tại trình duyệt |
| Thư viện | Tra cứu nguồn ngay cả khi generation bị tắt hoặc đạt giới hạn |
| Đánh giá | Hiển thị kết quả có provenance và cảnh báo khi khác corpus hoặc cấu hình |

Corpus chỉ chứa nguồn Vành đai 4 và luật chung liên quan. Request chỉ định dự án khác bị từ chối. Tin dự án được dùng làm bối cảnh, không làm bằng chứng độc lập cho quyền lợi cá nhân.

## Ngoài phạm vi

Không xác định thửa đất hoặc ranh giới bằng GIS, tính số tiền cho hồ sơ riêng, bảo đảm quyền được bồi thường hoặc tái định cư, tiếp nhận upload hồ sơ, quản lý tài khoản, thanh toán hoặc tự động cập nhật nguồn. Không bổ sung pipeline, model hoặc hạ tầng mới chỉ để mở rộng tính năng.

## Hành vi khi không thể trả lời đầy đủ

- Thiếu hồ sơ cá nhân: hỏi thông tin đã ẩn danh và giải thích vì sao chưa thể kết luận.
- Thiếu nguồn hoặc quan hệ pháp lý chưa xác minh: loại kết luận chưa được hỗ trợ và nêu giới hạn.
- Nguồn cần rà soát: dừng generation; giữ khả năng đọc nguồn.
- Quota, cold start hoặc provider giới hạn: thông báo tình trạng thực tế, không tạo câu trả lời thay thế giả.
- Hủy hoặc mất SSE: giải thích server không lưu đáp án để khôi phục; chỉ tạo lượt mới khi người dùng chủ động.
- Không lưu được lịch sử: thông báo hội thoại chỉ còn trong tab, không chuyển sang lưu server.

## Tiêu chí chấp nhận

| Nhóm | Tiêu chí |
|---|---|
| Chứng cứ | Không phát draft trước verify; không đồng nhất trích dẫn khớp với diễn giải đúng |
| Ngữ cảnh | Assistant message và citation do client gửi không được coi là nguồn pháp lý |
| Quyền riêng tư | Không lưu nội dung hội thoại trong database, log hoặc backup của ứng dụng |
| API | Tách phiên, chống gửi trùng và giữ deadline; client không được tự chọn operator |
| Giao diện | Sử dụng được trên desktop/mobile, bàn phím và hai chế độ sáng/tối |
| Khôi phục | Corpus Release xác minh checksum và restore được vào database riêng |
| Đánh giá | Bộ câu hỏi khóa trước chỉnh prompt; giữ attempt và công bố lỗi còn lại |

Tiêu chí chất lượng và phương pháp đo nằm trong [đánh giá](EVALUATION.md). Việc một yêu cầu được ghi trong PRD không phải xác nhận implementation đã đáp ứng; kết quả thực tế được ghi trong artifact của phiên bản tương ứng.

## Ràng buộc

Giữ một pipeline Agentic RAG, Groq GPT-OSS 120B, embedding E5 hiện tại và hosting Free. Giới hạn workflow được quy định trong [kiến trúc](ARCHITECTURE.md); quota public và quy trình xử lý sự cố nằm trong [vận hành](OPERATIONS.md).
