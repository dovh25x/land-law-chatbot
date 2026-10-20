# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd85651ee61610a0a38df495c8c03cf60c494b4a71aad246b6c7a92d3cf878d2`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 0 partial, 4 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; not independent legal certification; AI technical rubric/snapshot review; zero-LLM guard results identified, no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | insufficient_evidence | 32.76 | Không áp dụng | fail |
| N02 | insufficient_evidence | 10.98 | Không áp dụng | fail |
| N03 | insufficient_evidence | 9.30 | Không áp dụng | fail |
| N04 | insufficient_evidence | 14.24 | Không áp dụng | fail |
| N05 | answered | 8.00 | True | pass |
| N06 | answered | 9.78 | True | pass |
| N07 | clarification_needed | 0.29 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.28 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 2 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 5 | 1 | 0 | 4 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 85640 | 9543.5 | 32761 |
| token_usage | 8 | 43114 | 6537.5 | 8655 |
| llm_calls | 8 | 14 | 2.0 | 4 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Abstention an toàn sau chặn checklist/authority tự thêm, chưa trả lời khoản bồi thường có nguồn.
- N02: Abstention an toàn sau chặn mất điều kiện hỗ trợ; chưa giải thích được các yếu tố theo gold.
- N03: Abstention an toàn sau chặn điều kiện chuyển nghề; chưa đáp ứng tác vụ có nguồn.
- N04: Abstention an toàn sau chặn biến giả định người dùng thành điều kiện pháp luật; chưa nêu nguyên tắc trước thu hồi.
- N05: Nêu UBND cấp tỉnh đúng khoản2 Điều104, không tự gán thẩm quyền sang khoản1.
- N06: Đúng QĐ40/2026 ngày02/04/2026 thay QĐ56/2024; chỉ chỉ dẫn văn bản, không áp dụng quyền lợi vào hồ sơ cũ.
- N07: Hỏi ngày quyết định/phương án, không bảo đảm suất tái định cư.
- N08: Không xác nhận số hiệu giả, 50 tỷ hoặc suy không tồn tại chỉ vì thiếu trong corpus.
