# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-caf3c0833096ea4e`; fingerprint: `817e38259d90a2ac6b31650fb3092cc18fccd25d7ebbbdd504ecbd98cb0737f5`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 1 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering review against frozen rubric and cited source excerpts; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 12.99 | True | pass |
| N02 | insufficient_evidence | 12.53 | Không áp dụng | fail |
| N03 | limited | 32.87 | Không áp dụng | fail |
| N04 | insufficient_evidence | 15.61 | Không áp dụng | fail |
| N05 | answered | 3.46 | True | pass |
| N06 | answered | 10.45 | True | partial |
| N07 | clarification_needed | 0.04 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.02 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 3 | 2 | 1 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 87974 | 11490.5 | 32872 |
| token_usage | 8 | 51486 | 8218.5 | 9707 |
| llm_calls | 8 | 26 | 3.5 | 6 |
| tool_calls | 8 | 51 | 5.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí tháo dỡ/di chuyển/lắp đặt với thiệt hại máy móc theo Điều 104; không bảo đảm số tiền. Lượt key mới hoàn tất, một phản hồi TPM vẫn nằm trong attempt.
- N02: Abstain: không đáp ứng nội dung rubric. Trace có claim 30 kg gạo chưa có supporting span đúng nguồn; không tính từ chối an toàn là đạt nội dung.
- N03: Vẫn limited sau 6 request, có phản hồi TPM. Không có câu trả lời được phát hành; giữ mọi attempt trước và sau cập nhật key.
- N04: Abstain: chưa đưa được căn cứ điều kiện bố trí tái định cư trước thu hồi theo rubric.
- N05: Nêu UBND cấp tỉnh; citation Điều 104 chứa khoản 2 đúng thẩm quyền.
- N06: Nêu đúng QĐ40/2026 thay QĐ56/2024 và hiệu lực 02/04/2026 theo Điều 2. Chưa nêu lưu ý đối chiếu chuyển tiếp/hồ sơ cũ theo toàn bộ rubric; không chấm pass đầy đủ.
- N07: Nhánh tất định: không bảo đảm suất, hỏi điều kiện/hồ sơ/thời điểm. Provider bị khóa và xác minh 0 request.
- N08: Nhánh tất định: không xác nhận số hiệu giả hoặc tiền. Provider bị khóa và xác minh 0 request.
