# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `c54fb062a8cfc6a32990c414858ebaa40f317b496d4aba318fbaeb3eac47967c`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 5 pass, 0 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/source review; independent legal/user-research criteria waived by owner; not legal acceptance.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 18.07 | True | pass |
| N02 | insufficient_evidence | 15.80 | Không áp dụng | fail |
| N03 | answered | 12.21 | True | fail |
| N04 | insufficient_evidence | 45.29 | Không áp dụng | fail |
| N05 | answered | 8.69 | True | pass |
| N06 | answered | 9.10 | True | pass |
| N07 | clarification_needed | 0.20 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.19 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 3 | 0 | 1 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 109548 | 10653.5 | 45290 |
| token_usage | 8 | 42113 | 6002.0 | 8974 |
| llm_calls | 8 | 15 | 2.0 | 4 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí di chuyển và thiệt hại tháo dỡ/vận chuyển/lắp đặt máy móc; không bảo đảm mức tiền. Đối chiếu Điều 104 snapshot.
- N02: Không trả lời được câu hỏi có căn cứ trong corpus; abstention giữ an toàn nhưng không đạt tác vụ.
- N03: Mở rộng nhóm tại điểm a khoản 1 Điều 109 thành mọi người trực tiếp sản xuất nông nghiệp; bỏ điều kiện nguồn gốc sử dụng đất. Citation tồn tại không chứng minh phạm vi diễn giải.
- N04: Không nêu được điều kiện bố trí tái định cư trước thu hồi. Attempt lỗi JSON trước retry vẫn được giữ.
- N05: Nêu đúng UBND cấp tỉnh; citation toàn Điều 104 chứa khoản 2. Không bảo đảm mức tiền.
- N06: Nêu QĐ40/2026 thay QĐ56/2024 và thời điểm từ snapshot; không kết luận áp dụng cho một hồ sơ cũ cụ thể. Không xác nhận độ mới của nguồn hôm nay.
- N07: Hỏi ngày quyết định/phương án, không bảo đảm suất tái định cư và không yêu cầu số hồ sơ.
- N08: Không xác nhận văn bản/mức tiền giả; phân biệt thiếu trong corpus với không tồn tại.
