# Ingress và public/operator quota

Trạng thái: chấp nhận.

## Quyết định

Cloudflare Function ký HMAC tới Render; Turnstile tại bước tạo phiên; API production luôn public, CLI trusted operator.

## Lý do và hệ quả

Chặn gọi vòng qua ingress và tách ngân sách trải nghiệm khỏi phát triển. Operator không vượt quota thật Groq. Quota token dựa trên usage không là trần tuyệt đối.
