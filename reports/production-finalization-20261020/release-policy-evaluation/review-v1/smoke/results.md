# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 4/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e409d8ac39e2edf6cf9f039704fcd5cee7d377a583c787d004e4dd694c17ac02`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 3 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; no independent legal certification; limited/not_run retained in denominators.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 6.00 | True | pass |
| S02 | clarification_needed | 3.81 | True | pass |
| S03 | answered | 5.72 | True | pass |
| S04 | limited | 9.40 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 2 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 0 | 0 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 0, "deterministic": 4, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 24930 | 5859.5 | 9405 |
| token_usage | 4 | 0 | 0.0 | 0 |
| llm_calls | 4 | 1 | 0.0 | 1 |
| tool_calls | 4 | 26 | 6.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đúng QĐ40/2026 thay QĐ56/2024 từ02/04/2026, theo thời điểm hỏi.
- S02: Nêu QĐ40/2026 chưa có hiệu lực tại01/03/2026 và hỏi mốc hồ sơ; không áp dụng tương lai.
- S03: Đúng bãi bỏ một phần Điều2 QĐ38/2025, không suy bãi bỏ toàn văn.
- S04: Limited do TPD200000. Giữ nguyên attempt, không coi là lỗi nội dung hoặc một đáp án đạt.
