# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 1/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `380801c7436b04ac3535585b949a937656bec603fa6db3197f313bcd8cb9401c`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 0 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full Article 19 parent; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N02 | answered | 20.38 | True | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 0 | 0 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 0 | 0 | 0 | 0 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 1, "deterministic": 0, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 1 | 20382 | 20382 | 20382 |
| token_usage | 1 | 7391 | 7391 | 7391 |
| llm_calls | 1 | 2 | 2 | 2 |
| tool_calls | 1 | 8 | 8 | 8 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N02: N02 vẫn không đạt: không nêu rõ điều kiện đủ bồi thường ở nhánh khoản 1; chuyển phạm vi xã/phường/thị trấn nơi có đất thu hồi tại thời điểm phê duyệt thành nơi có quyết định phê duyệt; bỏ nhánh nhận giao khoán tại khoản 2. Guard mới không chứng minh mọi diễn giải còn lại đúng. Chỉ chạy 1/8 ca natural, không thay kết quả full suite bằng ca đơn lẻ.
