# ADR 0004: Kết luận giới hạn bởi chứng cứ

**Trạng thái:** Chấp nhận

## Bối cảnh

Citation hoặc đoạn trích khớp nguồn chưa chứng minh diễn giải đúng. Với nội dung pháp lý, nhầm nhóm đối tượng thành điều kiện, bỏ ngoại lệ hoặc mở rộng phạm vi hiệu lực có thể làm người đọc hiểu sai quyền lợi.

## Quyết định

Không phát đáp án trước verify. Kết luận được biểu diễn thành claim độc lập và kiểm tra theo chủ thể, điều kiện, ngoại lệ, hệ quả cùng thời điểm áp dụng. Tin dự án chỉ làm bối cảnh; history và citation cũ không thay thế chứng cứ mới.

Khi claim thiếu căn cứ, repair trong ngân sách hoặc loại claim cùng phần phụ thuộc mất ngữ cảnh. Không tự nối điều kiện vào claim để làm claim vượt kiểm chứng. Nếu không thể giữ câu trả lời có nghĩa, nêu giới hạn hoặc hỏi bổ sung.

## Phương án không chọn

Không chấp nhận draft chỉ vì có citation hợp lệ hoặc trích đoạn khớp từ khóa. Không dùng kiến thức nhớ sẵn của model để lấp điều khoản còn thiếu, không giải thích dẫn chiếu khi chưa có nguồn tương ứng.

## Hệ quả

- Hệ thống có thể từ chối quá mức và không đạt tác vụ dù nguồn liên quan có trong corpus.
- Abstention có lợi cho kiểm soát rủi ro nhưng không tự động được chấm pass cho câu hỏi nội dung.
- Chất lượng cần được đo riêng bằng task success, citation integrity và faithfulness; không có chỉ số đơn lẻ thay thế việc rà soát điều kiện pháp lý.
- Budget và deadline là ràng buộc thiết kế; không tăng số lần gọi để che lỗi benchmark.

## Kiểm chứng

Giữ regression cho lỗi chủ thể–điều kiện, mệnh đề phụ thuộc, phạm vi hỗ trợ, thiếu nguồn dẫn chiếu và citation giả. Review đáp án cuối gắn checksum; dùng offline judge tách biệt với runtime verifier theo [phương pháp đánh giá](../EVALUATION.md).
