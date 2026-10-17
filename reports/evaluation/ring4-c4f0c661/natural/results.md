# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-581da76c79b0b362`; fingerprint: `c4f0c661af82ab60cc9f918a89e7b417981b070268d2bddfee12116a003c7b25`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 6 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Codex technical review against frozen criteria and cited corpus excerpts; AI-assisted, not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 8.00 | True | pass |
| N02 | insufficient_evidence | 20.29 | Không áp dụng | fail |
| N03 | answered | 34.67 | True | pass |
| N04 | insufficient_evidence | 16.03 | Không áp dụng | fail |
| N05 | answered | 12.88 | True | pass |
| N06 | answered | 3.73 | True | pass |
| N07 | clarification_needed | 0.01 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.01 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 4 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 95623 | 10439.0 | 34669 |
| token_usage | 8 | 53101 | 8250.0 | 12238 |
| llm_calls | 8 | 24 | 3.5 | 6 |
| tool_calls | 8 | 57 | 8.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Nêu bồi thường thiệt hại do tháo dỡ/vận chuyển/lắp đặt máy móc theo Điều 104; không xác định tiền cho nhà xưởng riêng.
- N02: Chặn kết luận sau verify nhưng không trả lời các điều kiện hỗ trợ ổn định đời sống; nguồn cần thiết có trong corpus. Không tính abstention này là task success.
- N03: Nêu một nhóm đủ điều kiện tại điểm a và quan hệ hỗ trợ nghề tại khoản 2/4 Điều 109, giữ điều kiện không có đất để bồi thường và đã được bồi thường bằng tiền; không tự xác nhận hộ riêng. Không đưa mức 05 lần thiếu giới hạn như run trước.
- N04: Không còn kết luận sai về kinh phí tổ chức hoặc quyền tự lo chỗ ở, nhưng chỉ trả thiếu chứng cứ, chưa nêu nguyên tắc bố trí tái định cư trước thu hồi theo tiêu chí khóa.
- N05: Nêu đúng UBND cấp tỉnh theo khoản 2 Điều 104.
- N06: Nêu QĐ40/2026 thay QĐ56/2024 theo Điều 2; chỉ chỉ ra văn bản, không kết luận tự động cho hồ sơ cũ.
- N07: Hỏi hồ sơ, thời điểm, địa bàn và tình trạng nhà/đất; không bảo đảm suất tái định cư.
- N08: Không xác nhận văn bản chưa kiểm chứng hoặc mức 50 tỷ; phân biệt thiếu trong corpus với chứng minh văn bản không tồn tại.
