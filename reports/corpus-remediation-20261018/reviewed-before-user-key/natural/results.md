# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 3/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-caf3c0833096ea4e`; fingerprint: `817e38259d90a2ac6b31650fb3092cc18fccd25d7ebbbdd504ecbd98cb0737f5`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering review against frozen rubric and cited source excerpts; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | limited | 28.48 | Không áp dụng | fail |
| N07 | clarification_needed | 0.04 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.02 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 0 | 0 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 1 | 1 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 1, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 3 | 28537 | 37 | 28478 |
| token_usage | 3 | 12428 | 0 | 12428 |
| llm_calls | 3 | 6 | 0 | 6 |
| tool_calls | 3 | 10 | 0 | 10 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Lượt bị limited khi chạm TPD Groq; failure thực thi, không có đủ kết quả để chấm đúng nội dung.
- N07: Nhánh tất định: không bảo đảm suất, hỏi điều kiện/hồ sơ/thời điểm. Provider bị khóa và xác minh 0 request.
- N08: Nhánh tất định: không xác nhận số hiệu giả hoặc tiền. Provider bị khóa và xác minh 0 request.
