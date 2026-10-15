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

## Thanh đầu trang gọn (15/10/2026)

Theo yêu cầu cập nhật, phần đầu trang còn một hàng 56 px trên desktop/mobile; thay cho tổng 176 px của ba hàng desktop trước đó. Dự án và ngày áp dụng chuyển vào popover “Phạm vi” cạnh ô nhập; phạm vi đã chọn hiện bằng nhãn rút gọn. Agentic/Baseline đặt cạnh đó ở cả hai kích thước. Nút thông tin góc phải mở trạng thái kết nối, ngày kiểm tra, corpus, giới hạn dữ liệu và nút thử lại.

Màn hình bắt đầu đặt tiêu đề và ô nhập ở giữa, gợi ý thành các nút nhỏ. Khi có hội thoại, ô nhập ở dưới và nội dung cuộn riêng. Các nguồn và agent trace giữ nguyên. Popover hỗ trợ Escape, click ngoài, đặt lại và giới hạn trong viewport; panel hỗ trợ focus trap và trả focus khi đóng.

`reports/ui-compact-live.json` ghi kiểm tra UI đã triển khai, tách khỏi bằng chứng pháp lý và các lượt chat trước. Chạy `node scripts/verify_live_ui.mjs --skip-chat` để xác minh thay đổi giao diện mà không phát sinh lượt gọi LLM.
