# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e409d8ac39e2edf6cf9f039704fcd5cee7d377a583c787d004e4dd694c17ac02`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 6 pass, 1 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; no independent legal certification; limited/not_run retained in denominators.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 12.34 | True | partial |
| N02 | answered | 17.68 | True | pass |
| N03 | answered | 44.66 | True | pass |
| N04 | insufficient_evidence | 20.61 | Không áp dụng | fail |
| N05 | answered | 16.25 | True | pass |
| N06 | answered | 15.97 | True | pass |
| N07 | clarification_needed | 0.27 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.26 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 5 | 4 | 1 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 2 | 1 | 0 | 1 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 128048 | 16112.0 | 44664 |
| token_usage | 8 | 46015 | 6057.0 | 11012 |
| llm_calls | 8 | 15 | 2.0 | 4 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Nêu hai loại khoản chi phí và thiệt hại máy móc khi di dời do thu hồi, không nêu số tiền; chưa nói rõ thiệt hại phát sinh trong quá trình tháo dỡ/vận chuyển/lắp đặt, nên chưa chấm đủ rubric.
- N02: Giữ đúng nhánh hộ/cá nhân dùng đất nông nghiệp đủ điều kiện bồi thường; trích đúng tỷ lệ diện tích, có/không di chuyển, vùng khó khăn và thời gian trong nhánh khoản1. Không loại trừ nhánh khác hoặc kết luận cho hộ cụ thể.
- N03: Sau repair, giữ nguyên điều kiện nguồn gốc đất, không có đất để bồi thường và đã bồi thường bằng tiền trước quyền được hỗ trợ đào tạo/chuyển nghề/tìm việc. Không bảo đảm kết quả hồ sơ; câu còn mang cách diễn đạt điều luật.
- N04: Abstention an toàn vì draft ghép chưa có chỗ ở mới với nghĩa vụ thông báo khác; nguồn có quy tắc trước quyết định nhưng chưa trả lời thành công. Không tính refusal này là đúng tác vụ.
- N05: Đúng UBND cấp tỉnh, khoản2 Điều104; không gán thẩm quyền vào khoản1.
- N06: Đúng QĐ40/2026 thay QĐ56/2024 và ngày02/04/2026; chỉ dẫn văn bản, không áp dụng vào quyền lợi của hồ sơ cũ.
- N07: Hỏi ngày quyết định/phương án, không bảo đảm suất tái định cư.
- N08: Không xác nhận số hiệu giả hoặc mức50tỷ; không suy không tồn tại từ corpus thiếu.
