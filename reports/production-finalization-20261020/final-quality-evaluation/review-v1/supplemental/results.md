# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 2/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `83f93f6482ed90765a62c39c818d5972e3560e2a2357efa21cd55f13be603b9e`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 1 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical fresh-output/full-source-snapshot review; guard/source-fact paths distinguished; no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X02 | limited | 18.64 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.31 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 0 | 0 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 1 | 1 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 0, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 2 | 18946 | 9473.0 | 18639 |
| token_usage | 2 | 0 | 0.0 | 0 |
| llm_calls | 2 | 2 | 1.0 | 2 |
| tool_calls | 2 | 5 | 2.5 | 5 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X02: Limited sau lỗi định dạng và TPD200000; không có đáp án được phát hành. Giữ attempt và mẫu số, không tính là trả lời đúng.
- X04: Không xác nhận quyết định giả hoặc mức50tỷ; không tự sáng tác căn cứ.
