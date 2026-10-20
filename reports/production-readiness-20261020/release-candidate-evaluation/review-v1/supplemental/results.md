# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 1/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd85651ee61610a0a38df495c8c03cf60c494b4a71aad246b6c7a92d3cf878d2`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 1 pass, 0 partial, 0 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/snapshot review; zero-LLM guard results identified, no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X04 | insufficient_evidence | 0.20 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 0 | 0 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 1 | 1 | 0 | 0 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 0, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 1 | 203 | 203 | 203 |
| token_usage | 1 | 0 | 0 | 0 |
| llm_calls | 1 | 0 | 0 | 0 |
| tool_calls | 1 | 0 | 0 | 0 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X04: Không xác nhận số hiệu giả hoặc mức 50 tỷ; nêu thiếu chứng cứ trong corpus và cần nguồn chính thức.
