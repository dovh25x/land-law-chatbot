# Demo khoảng 10 phút

Chỉ demo pháp lý sau khi release được công bố và `/readyz` + smoke thành công. Nếu còn blocker, trình bày trạng thái thật trong `IMPLEMENTATION_STATUS.md`, không giả lập câu trả lời.

Hiện có thể mở https://hanoi-land-law.pages.dev để xem giao diện, ba hồ sơ dự án và trạng thái corpus; hỏi một câu để kiểm tra SSE, trace và hành vi thiếu căn cứ. Đây là demo hạ tầng, chưa thực hiện kịch bản hỏi đáp pháp lý dưới đây. API đang chạy tại https://land-law-chatbot.onrender.com trên Render Free.

1. **Phút 0–1:** mở URL Cloudflare, chờ backend khởi động. Nêu phạm vi Hà Nội, tài liệu công khai, không upload hồ sơ/tính tiền/GIS từng thửa. Xem ngày kiểm tra nguồn.
2. **Phút 1–3:** hỏi “Đất nông nghiệp bị thu hồi ở Hà Nội được bồi thường và hỗ trợ theo những điều kiện nào?”. Mở nguồn trích dẫn; đối chiếu điều/khoản và điều kiện còn thiếu. Hỏi tiếp “Nếu chưa có giấy chứng nhận thì cần kiểm tra thêm gì?” để xem hội thoại.
3. **Phút 3–5:** xem QĐ 56/2024 tại 01/04/2026 và 02/04/2026; agent phải kiểm tra văn bản thay thế và chuyển tiếp. Mở trace công cụ/quan hệ, không trình bày suy nghĩ nội bộ.
4. **Phút 5–7:** chọn lần lượt Vành đai 4, sông Hồng và Olympic. Hỏi “Tin khởi công có chứng minh thửa đất của tôi bị thu hồi hay được tái định cư không?”. Xem giới hạn của tin chính thức và nguồn dự án. Không suy ra vị trí thửa từ mô tả dự án.
5. **Phút 7–8:** hỏi không dấu hoặc địa bàn huyện cũ “dat o huyen Thanh Tri cu co duoc boi thuong khong?”. Agent cần địa chỉ/xã mới, không ánh xạ toàn huyện sang một xã.
6. **Phút 8–10:** xem báo cáo hai chế độ cùng corpus/model/dataset. Trình bày Recall@8, rubric, support, p95/calls và các ca không cải thiện. Phân biệt kết quả đã rà soát với pending/null; minh họa hết quota/cold start từ kiểm thử vận hành, không làm cạn quota thật chỉ để demo.

Nghiệm thu cần URL hoạt động, báo cáo benchmark acceptance đạt, source coverage đạt (có toàn văn lịch sử QĐ56), kiểm thử trọng yếu, bảo vệ phiên, restore/rollback và smoke. Giao diện đẹp hoặc unit tests pass không thay thế các bằng chứng đó.
