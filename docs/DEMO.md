> **Kịch bản hiện hành:** xem [demo đồ án](submission/DEMO.md). Nội dung bên dưới là kịch bản production/demo lịch sử, không phải yêu cầu nộp học phần.

# Demo kỹ thuật khoảng 10 phút

Mở https://hanoi-land-law.pages.dev. Corpus `corpus-de584c31fc95f9a2` đã công bố: 69 tài liệu/7.610 vector, NVIDIA `nvidia/nemotron-3-super-120b-a12b` và E5 ONNX 384 chiều. Nhãn “Demo kỹ thuật — chưa nghiệm thu pháp lý” và ngày kiểm tra nguồn luôn hiển thị. Benchmark đầy đủ còn pending; không trình bày tập core sáu lượt như tỷ lệ chất lượng toàn hệ thống.

1. **Phút 0–1:** xem nhãn, ngày kiểm tra và các nguồn còn thiếu; giới thiệu phạm vi Hà Nội, tình huống đã ẩn danh và ba dự án. Backend Render Free có thể cần khởi động.
2. **Phút 1–3:** hỏi “Quyết định 56/2024/QĐ-UBND Hà Nội còn hiệu lực ngày 12/10/2026 không, văn bản nào thay thế?”. Mở Điều2 QĐ40, link Công báo và trang PDF. Xem trace tra cứu/quan hệ hiệu lực. Luồng này đã chạy thật trên browser.
3. **Phút 3–5:** đặt thời điểm 02/08/2024, hỏi “Điều 104 Luật Đất đai 2024 quy định bồi thường chi phí di chuyển tài sản như thế nào?”. So sánh baseline/agentic, mở nguồn đầy đủ và xem calls/latency. Sáu kết quả core NVIDIA đã đối chiếu nguồn; cả baseline và agentic trả lời thật qua HTTPS với Điều104 khớp nguồn (xem `reports/live-demo.json`). Không gọi mẫu kiểm tra vận hành là nghiệm thu pháp lý đầy đủ.
4. **Phút 5–6:** đặt thời điểm 12/10/2026, hỏi “Nhà tôi sắp bị thu hồi. Tôi chắc chắn được một căn tái định cư đúng không?”. Hệ thống cần loại đất, giấy tờ, mốc phương án/quyết định và điều kiện di chuyển chỗ ở; không hứa quyền lợi hộ. Hành vi này đã source-review ở cả hai chế độ.
5. **Phút 6–8:** mở Thư viện văn bản (69 nguồn), ba hồ sơ Vành đai4/sông Hồng/Olympic (năm nguồn mỗi dự án). Phân biệt bối cảnh công khai với căn cứ thu hồi/thửa và quyền lợi hộ. Tải lại trang để kiểm tra hội thoại; nguồn và trace vẫn mở được. Có thể thử câu tiếp nối và câu không dấu; đánh giá rộng hơn còn đang hoàn thiện.
6. **Phút 8–10:** xem báo cáo và giải thích trạng thái pending/null, cấu hình/release được đánh giá. Trình bày pipeline, vector Colab/CPU runtime, giới hạn workflow, session isolation, SSE sau verifier, backup/restore và CI. Không tuyên bố agentic luôn tốt hơn baseline hoặc lấy hai mẫu latency làm p95.

Receipt: `reports/live-demo.json`, `live-ui.json`, `technical-release-gate.json`, `publication.json`, `runtime-tests.json` và `ci.json`. Full gate 20 cặp smoke và nghiệm thu 80 câu vẫn giữ nguyên; xem `IMPLEMENTATION_STATUS.md` và `OPERATIONS.md` để tiếp tục.

Hạn chế đã biết trên cấu hình Groq trước đây (chưa đánh giá lại đầy đủ trên NVIDIA): ca hỏi tiếp nối “Văn bản thay thế vừa nêu thay thế những quyết định nào?” sau câu QĐ56→QĐ40 chưa thành công trong hai lượt live vì throttling/budget và truy xuất chưa giải tham chiếu ổn định. Luồng lưu/tải lại hội thoại đã đạt; không trình bày hai việc này là một. Trong demo có thể nêu rõ số văn bản/điều để tra cứu, và trình bày ca limited như hạn chế đã ghi nhận.
