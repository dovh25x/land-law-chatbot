# Public chat acceptance — 22/10/2026

- Chạy bởi workflow `39739696869` qua public Pages ingress, không gọi trực tiếp Render.
- `generation.json`: **pass**.
- Challenge mode: `disabled`; `turnstile_token_observed=false`, `turnstile_script_requested=false`.
- Model: `openai/gpt-oss-120b`; `first_llm_calls=1`, `follow_up_llm_calls=1`.
- Follow-up giữ `history` và cùng `session_id`; citation mở được; reload và xóa lịch sử đạt; server history trả `410`; session isolation đạt.
- Corpus: `corpus-1afca764aa6692e0`; runtime fingerprint `07fc4e98e8ca25140012c6939db98cef7c8f0110845b94cef58d27de2481c70b`.
- Ảnh `navigation-*.png` chụp desktop 1440 và mobile emulated 390/320; không có thiết bị vật lý.
- Đây là acceptance kỹ thuật, không phải thẩm định pháp lý độc lập.

## Attempt trước

`attempts/generation-attempt-1-fingerprint.json` là lần chạy local đầu tiên, dừng ở bước fingerprint vì `.env` local đặt `ALLOW_STALE_GENERATION=true` trong khi production dùng `false`. Sau đó phát hiện thêm site key Turnstile bị lọt vào build disabled do biểu thức GitHub Actions; đã sửa ở commit `06ddbf3` và chạy lại workflow thành công. Các lần lỗi không được dùng làm acceptance.
