# Thiết kế và handoff frontend

[Figma · Vành đai 4](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=4-186) trong team `codex` là nguồn thiết kế. Connector tạo file được nhưng `send_prompt` và `get_chat_threads` không khả dụng. Sau khi thử lại, người dùng cho phép thiết kế trực tiếp trong Figma; bản này được dựng bằng Figma Plugin API, không phải output của Code agent.

## Brief và quyết định

Trải nghiệm hội thoại tham khảo ChatGPT: ưu tiên đọc đáp án dài, lịch sử tại máy, thao tác mobile rõ. Tiếng Việt, danh tính Vành đai 4; không chọn model/retrieval/project. Palette trung tính; Be Vietnam Pro; cột đọc 760 px, sidebar 264 px, composer bo 24 px; light/dark. Thư viện nguồn và đánh giá là điều hướng phụ. Nguồn mở drawer 420 px desktop, toàn màn hình mobile. Trace là chi tiết tự chọn.

Frames: desktop light `4:186`, dark `4:216`, mobile `4:246`, khởi đầu `5:8`, source drawer `5:14`, trạng thái `5:20`, thư viện `7:8`, đánh giá `7:15`. Đã dùng Simple Design System button làm tham chiếu. Repo không có package component SDS tương ứng; triển khai bằng button hiện có và CSS tokens. Bản sửa của chủ dự án được đọc lại và áp dụng ngày 2026-10-17: sidebar sáng `#f9f9f9`, user message có viền trên desktop, header hai dòng, thẻ gợi ý đánh số, action nguồn/thực thi/sao chép và các thẻ nguồn/metric. Icon gửi mobile lấy từ Figma tại `frontend/public/figma/arrow-up.svg`; không dùng URL asset tạm khi chạy. Các thao tác lưu trữ, xác minh trình duyệt và kết nối được giữ hoạt động trong bố cục mới.

`App.tsx`: hội thoại, điều hướng, nguồn, trace. `history.ts`: lưu/xóa/TTL và context request. `Turnstile.tsx`: challenge tạo phiên. `ui.tsx`: nguồn, trace và dữ liệu. CSS sáng/tối lấy giá trị từ frames; không giữ selector dự án trong luồng chat.

## Kiểm tra handoff

Đối chiếu desktop/mobile với frame, gồm cột đọc, màu, composer và sidebar. Chạy E2E fixture cho gửi/hỏi tiếp, history qua reload, xóa, expiry và lỗi storage. Kiểm tra keyboard Tab/Escape, focus về nút mở, không tràn ngang ở 320 px, dark mode, đáp án dài cuộn tới cuối và composer không che nội dung. Không dùng screenshot Figma làm asset giao diện.

Cold start và lỗi hiển thị lời giải thích thật. Mất SSE không tự gửi lại; nguồn/trace của đáp án đã nhận mở từ dữ liệu tại máy. Không tạo chức năng minh họa không có backend.
