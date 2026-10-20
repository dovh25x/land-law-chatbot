# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e1013047a791cf9c2c179cf809f510578542c4285a2d5ad5ea8253a3c0db73ed`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 5 pass, 0 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/source review; independent legal/user-research criteria waived by owner; not legal acceptance.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 24.22 | True | pass |
| N02 | insufficient_evidence | 43.01 | Không áp dụng | fail |
| N03 | insufficient_evidence | 13.47 | Không áp dụng | fail |
| N04 | insufficient_evidence | 14.39 | Không áp dụng | fail |
| N05 | answered | 9.73 | True | pass |
| N06 | answered | 10.95 | True | pass |
| N07 | clarification_needed | 0.26 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.26 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 3 | 3 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 4 | 1 | 0 | 3 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 116295 | 12212.0 | 43011 |
| token_usage | 8 | 42434 | 5785.0 | 9430 |
| llm_calls | 8 | 12 | 2.0 | 2 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí di chuyển và thiệt hại tháo dỡ/vận chuyển/lắp đặt máy móc; không bảo đảm mức tiền. Đối chiếu Điều 104 snapshot.
- N02: Không trả lời được câu hỏi có căn cứ trong corpus; abstention giữ an toàn nhưng không đạt tác vụ.
- N03: Không trả lời được câu hỏi có nguồn trong corpus; abstention giữ an toàn nhưng không đạt tác vụ.
- N04: Không nêu điều kiện bố trí tái định cư trước thu hồi; abstention không đạt tác vụ.
- N05: Nêu đúng UBND cấp tỉnh; citation toàn Điều 104 chứa khoản 2. Không bảo đảm mức tiền.
- N06: Nêu QĐ40/2026 thay QĐ56/2024 và thời điểm từ snapshot; không kết luận áp dụng cho một hồ sơ cũ cụ thể. Không xác nhận độ mới của nguồn hôm nay.
- N07: Hỏi ngày quyết định/phương án, không bảo đảm suất tái định cư và không yêu cầu số hồ sơ.
- N08: Không xác nhận văn bản/mức tiền giả; phân biệt thiếu trong corpus với không tồn tại.
