# Rà soát phạm vi MVP

## Giữ
Backend Agentic RAG/Groq/E5; frontend chat, nguồn, trace, thư viện, Vành đai 4, đánh giá; manifest/corpus/quan hệ/địa bàn; migrations; CI, deploy, đánh giá thủ công; backup/restore và phương pháp Colab E5. Giữ kiểm tra nguồn, phiên và công cụ chỉ đọc.

## Xóa/thu gọn
Baseline không có kết quả so sánh đầy đủ; provider Gemini/Workers AI/NVIDIA; benchmark production 120/80 và gates accepted; workflow cập nhật/embedding tự động; provisioning và script thử quota/multi-provider; báo cáo lịch sử, screenshot và bản xuất trùng; tài liệu M0–M6; báo cáo học phần, slide, kịch bản/video và trình tạo chúng. Các nguồn dự án khác vẫn nằm trong thư viện, nhưng không có điều khiển hỏi đáp dự án ngoài Vành đai 4.

## Thay đổi chưa commit trước đợt rà soát
Patch bổ sung mở luật tham chiếu chưa phát hành được lưu ở `/tmp/landlaw-before-mvp-cleanup/working-changes.patch` và loại khỏi bản nộp. Các báo cáo/nghiệm thu cũ không đại diện runtime mới đã được bỏ. Lịch sử Git vẫn lưu mã đã commit; secret/corpus/model và backup công khai được giữ ngoài Git.

## Nguyên tắc
Không drop schema cloud. Migrations đa chiều cũ được giữ để database mới vẫn chạy được; runtime chỉ nhận contract E5. Đọc publication metadata cũ để restore snapshot hiện có, nhưng public status luôn là học thuật. Chỉ kết quả mới đúng fingerprint mới được mô tả là bản bàn giao.
