# UI UX Redesign — Vành đai 4

[Figma: UI UX Redesign](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=14-2) · [Desktop](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=14-105) · [Mobile](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=14-115)

Giao diện hội thoại được tổ chức lại với sidebar thu gọn, composer thống nhất, câu hỏi căn phải và citation theo từng đáp án. Nguồn desktop từ 1280 px là vùng đối chiếu độc lập; màn hình nhỏ hơn dùng modal drawer. Thư viện, đánh giá, lịch sử, trace và trạng thái dịch vụ dùng cùng hệ thống màu/typography.

Frontend sử dụng endpoint trạng thái đã có; không đổi public API, schema lịch sử, pipeline, corpus, embedding hoặc hosting. Lỗi lưu tại máy và sao chép có ngữ cảnh riêng. Không tự gửi lại chat, không hiển thị draft trước kết quả và không tự tạo thời gian chờ.

## Bằng chứng

- `verification.json`: kết quả xác minh và checksum của source/ảnh trong lần bàn giao.
- `e2e-final.log`, `unit.log`, `build.log`, `secrets.log`: log kiểm tra. Các lần E2E trước được giữ riêng trong `e2e-attempt-*.log`.
- `matrix-*.png`: source panel và nội dung dài ở 320, 390, 768, 1024, 1280, 1440 px, sáng/tối, hai cấu hình trình duyệt desktop/mobile.
- `ui-figma-*.png`, `ui-revision-*.png`: ảnh từ implementation mới; không ghi đè artifact cũ.
- `contrast.json`: kiểm tra độ tương phản các cặp màu chữ/nền trong CSS.
- `figma.json`: ledger trang, token, component và frame. Figma dùng layer chỉnh sửa được, không dùng ảnh chụp màn hình làm giao diện.

Prototype có các điểm bắt đầu desktop/mobile sáng/tối; các luồng gồm soạn từ gợi ý, xử lý, đáp án/nguồn, thư viện, đánh giá và xác nhận xóa lịch sử. Nội dung mockup và dữ liệu E2E là fixture minh họa, không phải kết luận pháp lý hoặc số liệu chất lượng dịch vụ.

## Giới hạn kiểm chứng

Kiểm tra responsive và bàn phím chạy bằng Chromium/Playwright; kiểm tra ARIA/focus không thay thế thử với screen reader hoặc bàn phím ảo trên thiết bị thật. Chưa xác minh Safari/Firefox, deployment public, Groq hoặc Turnstile thật. Không chạy lại model evaluation và không thay bộ 20+4.

Figma diễn tả cấu trúc và trạng thái mẫu; nội dung dài trong ứng dụng được wrap/cuộn theo dữ liệu thực tế. Các frame ban đầu trong file Figma được giữ nguyên. Những thay đổi tài liệu khác đã có trong workspace trước tác vụ này được giữ nguyên.
