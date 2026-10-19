# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `8db2d701d6d27b69f3cb01615c9a8a16ef3a3fe74fb7c117721f2349f2a523dc`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 1 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full cited corpus passages; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 17.82 | True | pass |
| N02 | answered | 11.68 | True | fail |
| N03 | insufficient_evidence | 29.59 | Không áp dụng | fail |
| N04 | insufficient_evidence | 17.18 | Không áp dụng | fail |
| N05 | answered | 9.54 | True | pass |
| N06 | answered | 11.06 | True | partial |
| N07 | clarification_needed | 0.31 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.31 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 2 | 1 | 1 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 97483 | 11366.5 | 29595 |
| token_usage | 8 | 44007 | 5726.5 | 10444 |
| llm_calls | 8 | 14 | 2.0 | 4 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc trong quá trình đó; dẫn đúng Điều 104, không tính tiền.
- N02: Khái quát nhóm nhận giao khoán thành doanh nghiệp nhà nước, bỏ hợp đồng và các chủ thể/nguồn giao khoán cụ thể tại khoản 2 Điều 19; thêm kết luận mọi trường hợp thu hồi sau 01/08 áp dụng quy định trên chỉ từ hiệu lực/thay thế mà thiếu điều khoản chuyển tiếp. Citation khớp không chữa suy luận sai phạm vi.
- N03: Không có câu trả lời được phát hành. Draft đầu nêu đúng nhánh nguồn gốc đất/không có đất bồi thường/đã bồi thường bằng tiền và khoản 2 Điều 109, nhưng verifier nhầm với khoản 4 được dẫn chiếu; repair sửa số khoản theo nhận định sai và bị guard chặn. Không dùng fixture pass làm content pass.
- N04: Dù repair đã nhận draft tương ứng, model vẫn gán điều kiện chưa có chỗ ở mới cho quy định thông báo/công khai ở Điều 111 và bỏ điều kiện hoàn thành tái định cư trước quyết định thu hồi tại khoản 6 Điều 91. Không có kết luận được phát hành.
- N05: Nêu đúng UBND cấp tỉnh theo khoản 2 Điều 104.
- N06: Nêu đúng QĐ40 thay QĐ56 và thời điểm nhưng vẫn thiếu lưu ý kiểm tra thời điểm/phương án/chuyển tiếp trước áp dụng vào hồ sơ cũ; giữ cách chấm rubric như các lượt trước.
- N07: Hỏi hồ sơ/thời điểm cần thiết, không bảo đảm suất tái định cư.
- N08: Không xác nhận văn bản giả hoặc mức 50 tỷ; nêu thiếu căn cứ.
