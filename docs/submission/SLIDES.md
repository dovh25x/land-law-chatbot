# Slide thuyết trình (10 trang)

## 1. Tên đồ án
Hanoi Land Law Assistant — nguyên mẫu học thuật tra cứu pháp luật có agent. Điền nhóm/lớp/giảng viên.

## 2. Bài toán
Nguồn phân tán, văn bản dài và thay đổi theo thời điểm. Cần trả lời dễ hiểu kèm nguồn kiểm tra.

## 3. Phạm vi
Bồi thường, hỗ trợ, tái định cư Hà Nội. Vành đai 4 minh họa. Không tính tiền, không kết luận quyền lợi từng hộ, không tư vấn pháp lý đã thẩm định.

## 4. Tính liên ngành
Dữ liệu văn bản + AI/RAG + phần mềm web + tri thức miền. Minh họa bảng đóng góp trong báo cáo.

## 5. Kiến trúc
React → FastAPI → LangGraph → Supabase và Groq → kiểm tra → SSE. E5 Colab cho corpus và CPU cho truy vấn. Dùng sơ đồ báo cáo.

## 6. Dữ liệu và retrieval
Snapshot 69 tài liệu/7.610 vector. Nguồn, locator, checksum; hybrid keyword/vector. Không trộn embedding.

## 7. Agent
Tra cứu và mở điều khoản → tổng hợp → kiểm tra → trả lời/hỏi lại. Mở trace thực tế, không minh họa bằng lời gọi giả.

## 8. Demo
Hỏi Điều 104 → mở nguồn → mở trace → hỏi tiếp → xem Vành đai 4 → câu hỏi thiếu dữ kiện. Có video dự phòng.

## 9. Đánh giá
20/20 ca agentic chạy bằng Groq thật qua CLI quản trị trên corpus Supabase: 17 pass, 3 partial, 0 fail sau rà soát rubric/nguồn. S01 từng timeout và được thử lại; giữ cả 21 lần thực thi, đồng thời ghi nhận retry TPM trong lượt. S14 dùng lịch sử cố định; HTTP/browser kiểm chứng riêng. ID trích dẫn khớp không bảo đảm mọi mệnh đề đúng. Không gọi đây là nghiệm thu pháp lý hoặc kết quả SLA.

## 10. Hạn chế và bàn giao
Snapshot, truy xuất bỏ sót, provider/hosting miễn phí. URL, repo, hướng dẫn tái lập và kết quả từng ca. Hướng phát triển được tách khỏi phạm vi bài nộp.
