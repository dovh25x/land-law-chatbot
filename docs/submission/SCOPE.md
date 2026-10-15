# Phạm vi đồ án liên ngành

Tên: **Hanoi Land Law Assistant — nguyên mẫu học thuật tra cứu pháp luật có agent**.

Mục tiêu: minh họa xử lý dữ liệu văn bản, hybrid RAG, điều phối LangGraph và web full-stack. Chưa được thẩm định pháp lý độc lập; không thay thế cơ quan có thẩm quyền.

## Bản chốt

- Giữ website https://hanoi-land-law.pages.dev và API https://land-law-chatbot.onrender.com.
- Corpus hiện có: `corpus-de584c31fc95f9a2`, 69 tài liệu, 7.610 vector E5 ONNX Q8 384 chiều. Không embedding lại.
- Model: Groq `openai/gpt-oss-20b`; không chuyển model tự động.
- Tập trung bồi thường, hỗ trợ, tái định cư; Vành đai 4 là ví dụ dự án chính. Các tính năng khác được giữ nhưng không mở rộng cam kết.
- Bản cloud và mã nguồn có thể khác commit: xem receipt trong `reports/submission/` và `reports/deployment-current.json`. Không suy số liệu của bản local thành chất lượng bản cloud.
- Dữ liệu là snapshot có ngày kiểm tra trong `/readyz`, không cam kết cập nhật hằng ngày.

## Điều kiện nộp nội bộ

1. URL hoặc bản chạy local hoạt động; nguồn và trace mở được, hội thoại được lưu.
2. Có kết quả 20 câu agentic đúng cấu hình cloud; từng câu ghi kết quả thực tế và trạng thái rà soát. Không tự coi kết quả kỹ thuật là chấm đúng pháp lý.
3. Kiểm thử phần mềm và build đạt; không lộ secret, không truy cập chéo phiên.
4. Báo cáo, slide, kịch bản và video phản ánh đúng phiên bản chạy.
5. Công khai lỗi và giới hạn; không tuyên bố đã nghiệm thu pháp lý hay đạt các ngưỡng chất lượng chưa đo.

## Không còn là điều kiện nộp

M0–M6 production, 120 câu benchmark, 80 câu acceptance, SLA p95, cập nhật nguồn tự động, hoàn thiện mọi quan hệ pháp lý, so sánh nhiều model và diễn tập khôi phục bổ sung. Giữ bảo mật, kiểm tra nguồn và backup đã có. Các gate `demo`/`accepted` cũ vẫn nguyên nghĩa; phạm vi học phần không cấp trạng thái `accepted`.

Chưa có rubric giảng viên: đây là checklist nội bộ, cần đối chiếu khi nhận yêu cầu học phần.
