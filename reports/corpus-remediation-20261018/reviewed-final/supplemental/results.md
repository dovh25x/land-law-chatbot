# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-caf3c0833096ea4e`; fingerprint: `817e38259d90a2ac6b31650fb3092cc18fccd25d7ebbbdd504ecbd98cb0737f5`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering review against frozen rubric and cited source excerpts; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 3.00 | True | pass |
| X02 | insufficient_evidence | 14.83 | Không áp dụng | fail |
| X03 | insufficient_evidence | 41.81 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.01 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 1 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 3, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 59654 | 8915.0 | 41812 |
| token_usage | 4 | 33716 | 9195.5 | 15325 |
| llm_calls | 4 | 12 | 3.5 | 5 |
| tool_calls | 4 | 22 | 6.5 | 9 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Đủ chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc, không định giá.
- X02: Guard chặn khái quát sai danh mục/điều kiện; kết quả abstain an toàn nhưng chưa đáp ứng nội dung, không tính pass.
- X03: Chưa trả lời phân biệt đối tượng và điều kiện, quota/retry được giữ trong telemetry.
- X04: Không xác nhận số hiệu hoặc tiền; nêu giới hạn corpus và cần nguồn chính thức.
