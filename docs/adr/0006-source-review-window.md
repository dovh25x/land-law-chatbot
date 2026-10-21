# ADR 0006: Cửa sổ rà soát nguồn tối đa 72 giờ

**Trạng thái:** Đề xuất, chưa áp dụng. Chính sách 24 giờ hiện hành vẫn là nguồn có hiệu lực cho production.

## Bối cảnh

Source gate chỉ cho phép các đoạn đã được review trong một cửa sổ ngày cụ thể. Cửa sổ 24 giờ bảo vệ tính mới nhưng tạo nhịp vận hành hằng ngày; nếu một vòng quay bị lỡ, gate đóng và người dân không thể nhận câu trả lời có căn cứ. Người vận hành đã chọn một chính sách có bằng chứng dài 72 giờ, nhưng chưa có thay đổi nào được kiểm thử và phê duyệt.

Kéo dài thời hạn làm giảm số lần vận hành, đồng thời làm tăng phạm vi ảnh hưởng nếu nguồn hoặc hiệu lực pháp lý thay đổi. Vì vậy thời hạn dài hơn chỉ được chấp nhận khi mỗi vòng quay vẫn xác minh lại nguồn, kiểm tra hiệu lực và có đường rollback đã kiểm chứng.

## Quyết định đề xuất

Cho phép một scope rà soát mới có thời hạn tối đa **72 giờ** (ba ngày lịch, kết thúc exclusive), với các điều kiện bắt buộc:

1. **Xác minh nguồn lại từ đầu.** Chạy lại quy trình re-fetch chính thức cho toàn bộ tài liệu được ghim; tất cả checksum byte hoặc text phải khớp bản đã review. Không dùng thời gian trôi qua thay cho việc kiểm tra.
2. **Kiểm tra hiệu lực pháp lý và phạm vi.** Trước khi mở rộng, người review xác nhận không có văn bản sửa đổi/thay thế mới, không đổi quan hệ pháp lý, và từng đoạn được ghim vẫn có hiệu lực trong suốt cửa sổ. Đoạn nào không chắc chắn về hiệu lực hoặc applicability thì không được đưa vào scope mới.
3. **Append-only.** Scope mới chỉ được thêm vào receipt; mọi scope, checksum, text và lịch sử cũ được giữ nguyên. Không sửa artifact lịch sử để khớp chính sách mới.
4. **Chỉ gate sau replay.** Candidate phải được replay offline tại ngày bắt đầu, ngày cuối còn hiệu lực và ngày hết hạn; gate phải usable bên trong và fail closed tại `as_of_to`. Chỉ sau đó mới được ghi receipt bổ sung và cập nhật con trỏ gate.
5. **Phê duyệt và rollback.** Candidate policy phải có SHA256, biên bản review và con trỏ policy 24 giờ trước đó. Rollback phải đưa con trỏ về policy cũ với bộ receipt cũ còn nguyên; nếu chưa kiểm chứng rollback, giữ 24 giờ hoặc tắt generation và chỉ cho tra cứu nguồn.
6. **Không tự gia hạn.** Không có job nào tự động cộng thêm 72 giờ. Mỗi lần gia hạn là một vòng review có bằng chứng mới.

Cửa sổ đề xuất kế tiếp, nếu được duyệt, là `2026-10-23` → `2026-10-26` theo `Asia/Ho_Chi_Minh` (exclusive end), tức hết hạn lúc `2026-10-26 00:00` giờ Bangkok/Hà Nội. Đây chỉ là ví dụ để kiểm thử; chưa có receipt production nào được sửa.

## Phương án không chọn

- **Tự động gia hạn vô hạn:** che giấu việc nguồn đã cũ và biến warning thành tín hiệu vô nghĩa.
- **Chỉ dựa vào `ALLOW_STALE_GENERATION=true`:** bỏ qua scoped receipt gate và làm mất khả năng phân biệt đoạn đã review với snapshot chưa review.
- **Áp dụng 72 giờ cho toàn bộ corpus:** chỉ các đoạn được review trong scope mới được dùng; không có "whole corpus verified".
- **Sửa trực tiếp receipt cũ:** phá tính append-only, checksum và khả năng rollback.

## Hệ quả

- Giảm tần suất quay nguồn từ hằng ngày xuống tối đa ba ngày một lần, nhưng mỗi lần vẫn phải re-fetch, kiểm tra hiệu lực và replay.
- Blast radius của một lần review sai lớn hơn 24 giờ; do đó 72 giờ là **trần**, không phải mặc định, và có thể giữ 24 giờ nếu có nghi ngờ.
- Gate vẫn đánh giá theo ngày của từng câu hỏi; cửa sổ 72 giờ không cấp quyền cho câu hỏi lịch sử ngoài scope.
- `source_fresh` toàn corpus vẫn có thể là `false`; UI chỉ dùng các đoạn fresh trong gate và không biến warning thành tuyên bố đã xác minh toàn bộ.

## Kiểm chứng

- Test biên `tests/test_source_review_window_policy.py` xác nhận scope 72 giờ usable trong ba ngày và fail closed tại ngày exclusive kế tiếp.
- Quy trình vận hành và mốc hết hạn được ghi tại `reports/source-review-policy-20261022/README.md`.
- Chưa có thay đổi runtime, receipt production hoặc cấu hình Render trong ADR này. Việc áp dụng cần một candidate riêng, review pháp lý và phê duyệt của người vận hành.
