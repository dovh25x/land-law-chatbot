# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `4e8dd8d2b56789bfb2496f5c7b475162f2631813615f6289a1d8ab1a509a85e7`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 3 pass, 2 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full cited corpus passages; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 20.36 | True | pass |
| N02 | answered | 11.68 | True | fail |
| N03 | answered | 16.69 | True | partial |
| N04 | insufficient_evidence | 13.83 | Không áp dụng | fail |
| N05 | insufficient_evidence | 52.53 | Không áp dụng | fail |
| N06 | answered | 12.39 | True | partial |
| N07 | clarification_needed | 0.31 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.31 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 1 | 2 | 1 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 128091 | 13109.0 | 52532 |
| token_usage | 8 | 46018 | 5992.0 | 13511 |
| llm_calls | 8 | 16 | 2.0 | 6 |
| tool_calls | 8 | 48 | 7.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc trong quá trình đó; trích Điều 104, không tính tiền.
- N02: Đặt điều kiện đủ bồi thường như điều kiện chung của toàn bộ hỗ trợ rồi mới nêu ngoại lệ, làm sai phạm vi; khái quát mọi đất giao khoán mà thiếu chủ thể/nguồn giao khoán ở khoản 3 Điều 19. Citation parent đầy đủ không chữa diễn giải thiếu điều kiện.
- N03: Có thu nhập tại thời điểm phê duyệt và các nhóm loại trừ theo Điều 22 NĐ88, nhưng biến định nghĩa chủ thể thành bộ điều kiện đủ để hưởng hỗ trợ; chưa thể hiện điều kiện/nhánh đất trong Điều 109 Luật Đất đai.
- N04: Từ chối vì kiểm chứng chặn draft; chưa trả lời điều kiện hoàn thành bố trí tái định cư trước quyết định thu hồi theo khoản 6 Điều 91 dù nguồn có trong corpus.
- N05: Không nêu được UBND cấp tỉnh theo khoản 2 Điều 104; giới hạn TPM và chọn ngữ cảnh sai dẫn tới không có câu trả lời.
- N06: Nêu đúng QĐ40 thay QĐ56 và ngày văn bản, nhưng không có lưu ý kiểm tra thời điểm/quy định chuyển tiếp cho hồ sơ cũ như rubric đã khóa yêu cầu.
- N07: Hỏi hồ sơ/thời điểm và không bảo đảm suất tái định cư.
- N08: Không xác nhận văn bản giả hoặc 50 tỷ, nêu thiếu chứng cứ.
