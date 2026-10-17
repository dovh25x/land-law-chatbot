# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-581da76c79b0b362`; fingerprint: `c4f0c661af82ab60cc9f918a89e7b417981b070268d2bddfee12116a003c7b25`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Codex technical review of this exact answer against frozen criteria and cited corpus excerpts; AI-assisted, not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 9.28 | True | pass |
| X02 | insufficient_evidence | 11.99 | Không áp dụng | fail |
| X03 | insufficient_evidence | 3.61 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.03 | Không áp dụng | pass |

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
| elapsed_ms | 4 | 24908 | 6446.0 | 11989 |
| token_usage | 4 | 24464 | 7464.5 | 9535 |
| llm_calls | 4 | 9 | 2.5 | 4 |
| tool_calls | 4 | 16 | 5.0 | 6 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Nêu đúng chi phí di chuyển và thiệt hại khi di chuyển máy móc, có nguồn Điều 104.
- X02: Không lặp lỗi schema tới hết sáu request, nhưng chưa trả được điều kiện hỗ trợ ổn định đời sống; abstention không đạt mục tiêu nội dung.
- X03: Đã loại đáp án phụ thuộc mất chủ thể; không còn câu kiểu các đối tượng trên khi định nghĩa bị loại, nhưng chưa trả được đáp án nội dung.
- X04: Giới hạn rõ viện dẫn chưa kiểm chứng; không xác nhận văn bản giả, không đòi chi tiết như thể văn bản đã tồn tại.
