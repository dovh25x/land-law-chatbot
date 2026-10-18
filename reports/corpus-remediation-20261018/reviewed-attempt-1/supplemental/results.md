# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-caf3c0833096ea4e`; fingerprint: `ce30e830008a2e8997f20501dd3f0c1a9c1981d08afcc71a0ba2aaee2cb84312`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering review against frozen rubric and cited source excerpts; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 3.25 | True | pass |
| X02 | answered | 16.30 | True | fail |
| X03 | insufficient_evidence | 3.46 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.01 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 1 | 0 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 2 | 1 | 0 | 1 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 3, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 23025 | 3357.0 | 16302 |
| token_usage | 4 | 24919 | 7515.5 | 9888 |
| llm_calls | 4 | 10 | 2.5 | 5 |
| tool_calls | 4 | 18 | 5.0 | 8 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Đủ chi phí di chuyển và thiệt hại máy móc, không định giá.
- X02: Gom ba khoản hỗ trợ riêng thành ba loại chính, gộp điều kiện hợp đồng của nhóm riêng và dựa vào lời nối sau verify. Đây là lỗi tái hiện đã dẫn tới guard mới; không giữ làm bằng chứng chấp nhận.
- X03: Abstain an toàn nhưng chưa phân biệt đối tượng và điều kiện theo rubric.
- X04: Không xác nhận số hiệu hoặc tiền, nêu giới hạn corpus và cần nguồn chính thức.
