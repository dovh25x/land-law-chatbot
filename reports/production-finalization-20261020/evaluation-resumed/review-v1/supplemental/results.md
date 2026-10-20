# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd85651ee61610a0a38df495c8c03cf60c494b4a71aad246b6c7a92d3cf878d2`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 1 pass, 0 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; not independent legal certification; AI technical rubric/snapshot review; zero-LLM guard results identified, no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | insufficient_evidence | 51.25 | Không áp dụng | fail |
| X02 | answered | 16.12 | True | fail |
| X03 | insufficient_evidence | 6.21 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.20 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 0 | 0 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 3, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 73781 | 11166.0 | 51246 |
| token_usage | 4 | 23284 | 7287.5 | 8709 |
| llm_calls | 4 | 10 | 3.0 | 4 |
| tool_calls | 4 | 12 | 3.5 | 5 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Abstention an toàn nhưng chưa đáp ứng tác vụ có căn cứ về chi phí di chuyển; không tính là trả lời đúng.
- X02: Có đủ nhóm và phủ định tự động nhận nhưng mở rộng đối tượng Điều109: người có thu nhập ổn định từ sử dụng đất; mất điều kiện giao khoán, sản xuất nông nghiệp, không có đất và đã bồi thường bằng tiền. Claim được phát hành chứa diễn giải thiếu điều kiện.
- X03: Abstention an toàn nhưng không phân biệt được khoản1/khoản2 theo câu hỏi có nguồn.
- X04: Không xác nhận số hiệu giả hoặc mức 50 tỷ; nêu thiếu chứng cứ trong corpus và cần nguồn chính thức.
