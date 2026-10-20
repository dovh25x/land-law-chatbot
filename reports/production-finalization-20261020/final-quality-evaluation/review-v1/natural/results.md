# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 4/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `83f93f6482ed90765a62c39c818d5972e3560e2a2357efa21cd55f13be603b9e`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 0 partial, 0 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical fresh-output/full-source-snapshot review; guard/source-fact paths distinguished; no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 15.57 | True | pass |
| N04 | answered | 19.35 | True | pass |
| N07 | clarification_needed | 0.41 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.41 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 2 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 1 | 1 | 0 | 0 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 2, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 35748 | 7991.0 | 19354 |
| token_usage | 4 | 13430 | 3059.5 | 7311 |
| llm_calls | 4 | 4 | 1.0 | 2 |
| tool_calls | 4 | 14 | 1.5 | 11 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Giữ nguyên phạm vi hệ thống máy móc/dây chuyền và thiệt hại khi tháo dỡ/vận chuyển/lắp đặt, tách khỏi chi phí di chuyển. Không nêu tiền hoặc bảo đảm hồ sơ riêng.
- N04: Nêu đúng hoàn thành phê duyệt phương án và bố trí tái định cư trước quyết định thu hồi; không thay bố trí thực tế bằng phê duyệt phương án bố trí, không ghép15ngày hoặc tiền đề chưa có chỗ ở.
- N07: Hỏi ngày quyết định/phương án; không xác nhận suất tái định cư.
- N08: Không xác nhận số hiệu giả hoặc50tỷ; không suy văn bản không tồn tại chỉ vì thiếu trong corpus.
