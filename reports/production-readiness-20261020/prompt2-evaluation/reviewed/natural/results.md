# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e5e120495c80d63a4368d82dea3c1d38d177b07a7903bea398c3ad1abbf29d9c`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 0 partial, 4 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/source review; independent legal/user-research criteria waived by owner; not legal acceptance.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 47.58 | True | pass |
| N02 | answered | 50.03 | True | fail |
| N03 | insufficient_evidence | 12.55 | Không áp dụng | fail |
| N04 | insufficient_evidence | 20.86 | Không áp dụng | fail |
| N05 | answered | 8.48 | True | fail |
| N06 | answered | 10.97 | True | pass |
| N07 | clarification_needed | 0.21 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.20 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 2 | 0 | 2 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 150894 | 11760.5 | 50033 |
| token_usage | 8 | 52166 | 6523.5 | 12540 |
| llm_calls | 8 | 20 | 2.0 | 6 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí di chuyển và thiệt hại tháo dỡ/vận chuyển/lắp đặt máy móc; không bảo đảm mức tiền. Đối chiếu Điều 104 snapshot.
- N02: Nói hỗ trợ chỉ áp dụng nhóm đủ điều kiện bồi thường, trái nhánh khoản 2; đồng thời mở rộng nhóm giao khoán ngoài chủ thể nguồn. Đã tạo regression và guard ở SHA sau; không sửa artifact này.
- N03: Không trả lời được câu hỏi có căn cứ trong corpus; không tính abstention là trả lời đúng.
- N04: Không nêu được điều kiện bố trí tái định cư trước thu hồi; nguồn có nhưng đầu ra abstain.
- N05: Gán thẩm quyền UBND cấp tỉnh vào khoản 1 Điều 104; quy định đó nằm ở khoản 2. Đúng chủ thể nhưng sai căn cứ khoản, không đạt rubric.
- N06: Nêu QĐ40/2026 thay QĐ56/2024 và thời điểm từ snapshot; không kết luận áp dụng cho một hồ sơ cũ cụ thể. Không xác nhận độ mới của nguồn hôm nay.
- N07: Hỏi ngày quyết định/phương án, không bảo đảm suất tái định cư và không yêu cầu số hồ sơ.
- N08: Không xác nhận văn bản/mức tiền giả; phân biệt thiếu trong corpus với không tồn tại.
