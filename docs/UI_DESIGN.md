# UI từ Figma

Thiết kế: https://www.figma.com/design/E8ntRTL3j3J29fhMM62mDk/Hanoi-Land-Law-UI-Redesign

Tham chiếu chính: desktop bắt đầu `5:2`, đáp án `5:137`, nguồn `5:274`, trace `6:77`; mobile đáp án `7:592`. Mã React dùng bố cục flex/grid thay cho tọa độ cố định của bản thiết kế.

- Font Be Vietnam Pro được đóng gói tại build, không gọi CDN font khi chạy; giấy phép OFL đi cùng website ở `/licenses/BeVietnamPro-OFL.txt`.
- Màu và khoảng cách lấy từ bộ token Figma. Các icon dùng cùng Lucide với bản thiết kế.
- `ui.tsx` dùng chung DocumentRow, SidePanel, SourcePanel và TracePanel. Chữ và số liệu lấy từ API thật, không đưa dữ liệu minh họa của Figma vào production.
- Trên mobile, menu mở dạng drawer, nguồn/trace mở toàn màn hình, chọn baseline/agentic nằm trong composer; desktop giữ panel nguồn/trace cạnh hội thoại khi đủ rộng.
- Ngày để trống vẫn có nghĩa hôm nay theo hợp đồng API; không cố định ngày minh họa của Figma. Không thay đổi backend, model hay corpus.
- Trạng thái hiệu lực/nghiệm thu lấy từ API; có thể mở phạm vi dữ liệu và nguồn còn thiếu. Báo cáo không khớp cấu hình luôn có thông báo, dữ liệu chi tiết đặt trong phần mở rộng.

Kiểm tra: `npm test`, `npm run build`, `npm run test:e2e` trong `frontend/`. E2E dùng fixture tách biệt để kiểm tra UI, không phải benchmark pháp luật. `scripts/verify_live_ui.mjs` kiểm tra URL thật không mock và lưu receipt riêng; quota của API công khai được ghi rõ, không dùng kết quả fixture thay thế lượt hỏi thật.
