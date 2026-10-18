# Xác minh triển khai UI UX Redesign

Public: https://hanoi-land-law.pages.dev

Source đã deploy trên cả Cloudflare Pages và Render: `578d31f1f5f2622c9c60a39b7d7f286fc35935f0`.

## Đã xác minh

- CI đạt trên đúng SHA: [GitHub Actions](https://github.com/dovh25x/land-law-chatbot/actions/runs/39053156495). Checkout phát hành riêng cũng đạt backend, unit frontend, build và secret scan.
- Render báo `live`, plan Free; Cloudflare báo `success`. Canonical deployment và Render cùng SHA. Xem `deployment.json` và các log deploy.
- Giao diện public dùng API thật, không route interception, ở 1440, 390 và 320 px. Mobile là giả lập theo yêu cầu đã điều chỉnh. Mở được nguồn, thư viện, trang đánh giá; không tràn ngang.
- PostgreSQL, corpus Vành đai 4 có 59 tài liệu và fingerprint khớp mã nguồn. Báo cáo đánh giá khác cấu hình vẫn được cảnh báo, không coi là chất lượng của runtime PostgreSQL.
- Groq GPT-OSS 120B được gọi thật qua pipeline Agent hiện có, scope `operator`: kết quả `answered`, 4 LLM request, 8 tools, 1 citation. Đây là smoke kỹ thuật, không phải thẩm định chất lượng pháp lý.
- Hai probe schema kỹ thuật độc lập trước đó bị từ chối; giữ nguyên attempt. Pipeline ứng dụng có một HTTP 429 và retry trong budget; không thay key, model hoặc hosting. Xem cả ba file `groq-*.json`.
- Backend trực tiếp từ chối API không có signed ingress (403); public từ chối tạo phiên thiếu token Turnstile (400, `challenge_required`).

## Phần chưa hoàn tất

Turnstile thật đã tải và hiển thị ô “Verify you are human” (`live/turnstile.png`). Trình duyệt tự động không được cấp token trong lần chạy; không tự động bấm challenge, dùng test key hoặc tắt xác minh.

Vì vậy, chưa xác minh tạo phiên với token hợp lệ và toàn bộ public chat/hỏi tiếp/reload/xóa sau Turnstile. `live/generation.json` giữ trạng thái failed ở bước Turnstile; thành công của operator không thay thế public browser flow. Khi người dùng hoàn tất challenge trên trình duyệt thông thường, cần kiểm tra nốt các bước này.

## Bằng chứng và phạm vi

`verification.json` tổng hợp kết quả và checksum; `ci.json`, `deployment.json`, `groq-*.json`, `live/*.json` lưu metadata. Ảnh chỉ chụp navigation và widget trước khi có hội thoại; không ghi prompt, đáp án, token xác minh hoặc secret vào báo cáo.

Không đổi corpus, embedding, pipeline, database hoặc gói Free; không chạy lại bộ model evaluation. Các thay đổi tài liệu đang dở trong workspace được giữ nguyên; HEAD local được đồng bộ tới SHA đã deploy. Báo cáo mới này chưa commit.
