# Phạm vi phát hành production

Production tiếp tục dùng profile `academic` và nhãn `academic_prototype` của hệ thống hiện hành. Phát hành phần mềm không đổi profile thành được chứng nhận pháp lý, không biến nguồn pending thành chứng cứ và không đổi corpus chỉ để làm cổng chất lượng đạt.

Chủ dự án đã miễn yêu cầu reviewer pháp lý độc lập và nghiên cứu người dùng trước phát hành; biên bản ở `acceptance-waiver.json`. Rà soát trong đợt này là rà soát kỹ thuật bằng AI, không gán vai trò chuyên gia độc lập hoặc kết quả người dùng thật.

Quy trình vận hành hiện hành đã tách cổng rubric tùy chọn khỏi deploy (`docs/OPERATIONS.md`, `docs/redesign/CORPUS.md`, regression `test_default_deploy_preflight_does_not_require_model_review`). Cấu hình được đọc trước phát hành là `REQUIRE_QUALITY_READINESS=false`; đợt này không tắt một cổng đang bật, không sửa ngưỡng smoke/supplemental/natural và không ghi readiness chất lượng thành pass khi chưa đạt.

Điều kiện phát hành phần mềm: source đã commit và ghim SHA; năm kiểm tra phần mềm đạt; kiểm tra cấu hình Free, ingress, Turnstile và lưu metadata; corpus/fingerprint thật khớp sau deploy; nguồn/citation và layout truy cập được; giữ rollback. Các giới hạn model/corpus phải có số liệu và được công bố theo đúng cấu hình, giữ mọi attempt.

Corpus đang phục vụ giữ nguyên `corpus-a26bc99e541fbbe2`; không có vector được tạo lại, không restore đè database, không drop database hoặc gỡ Release cũ. Ba tài liệu mới chỉ vào catalogue reference-only, chưa tham gia retrieval/citation AI. Các khoảng trống pháp lý và mốc nguồn cũ vẫn được công bố, không có receipt freshness giả.

Bộ 48 tình huống v2 vẫn là dự thảo chưa freeze; không công bố điểm của chúng. Các bộ khóa cũ kiểm tra hồi quy, không đại diện đầy đủ nhu cầu người dân. Đánh giá mô hình thực được lưu riêng; ca chưa chạy/lỗi/abstention không bị loại mẫu số hoặc gọi là trả lời đúng. Bước public browser chat sẽ dùng Turnstile thật; nếu cần tương tác, ghi chưa xác minh và không bypass challenge.
