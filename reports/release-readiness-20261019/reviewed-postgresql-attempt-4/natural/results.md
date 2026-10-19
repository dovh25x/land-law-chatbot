# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `f6b7043209b1f8c20c1e24d2fa6b1a746a7ec2fb922a6f22597a506115345b8b`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 5 pass, 1 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full cited corpus passages; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 23.57 | True | pass |
| N02 | answered | 13.31 | True | fail |
| N03 | answered | 13.94 | True | pass |
| N04 | insufficient_evidence | 14.85 | Không áp dụng | fail |
| N05 | answered | 12.39 | True | pass |
| N06 | answered | 13.97 | True | partial |
| N07 | clarification_needed | 0.31 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.40 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 5 | 3 | 1 | 1 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 2 | 1 | 0 | 1 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 92751 | 13628.5 | 23572 |
| token_usage | 8 | 39272 | 6057.0 | 7715 |
| llm_calls | 8 | 12 | 2.0 | 2 |
| tool_calls | 8 | 44 | 5.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Nêu rõ chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc trong quá trình đó, đúng Điều 104; không tính số tiền.
- N02: Có các mốc tỷ lệ/thời gian, mức gạo và ngoại lệ dưới 30%/không đủ bồi thường. Tuy nhiên diễn đạt phạm vi diện tích thành nơi quyết định phê duyệt thay vì nơi có đất thu hồi tại thời điểm phê duyệt; thiếu nhánh sử dụng đất giao khoán với chủ thể/nguồn giao khoán và hợp đồng tại khoản 2 Điều 19. Chưa đủ điều kiện/phạm vi để đạt rubric.
- N03: Nêu đúng nhánh điểm a khoản 1 và hỗ trợ bổ sung khoản 2 Điều 109: chủ thể trực tiếp sản xuất, nguồn gốc đất, không có đất để bồi thường và đã được bồi thường bằng tiền. Không biến hỗ trợ thành bảo đảm quyền lợi cá nhân hoặc tính mức tiền.
- N04: Draft có câu đúng khoản 6 Điều 91 nhưng kèm trigger chưa được bố trí chỗ ở gán cho khoản 2 không có căn cứ. Verifier chặn; repair mất câu trả lời trọng tâm và tiếp tục gán trigger sai. Không có kết luận được phát hành.
- N05: Trả lời UBND cấp tỉnh theo khoản 2 Điều 104; không nhầm thẩm quyền cấp xã/huyện hoặc tổ chức cưỡng chế.
- N06: Nêu đúng QĐ40 thay QĐ56 và thời điểm, có thêm mốc QĐ56; vẫn thiếu hướng dẫn kiểm tra thời điểm/phương án/chuyển tiếp trước áp dụng cho hồ sơ cũ, theo rubric đã khóa và cách chấm lượt trước.
- N07: Hỏi hồ sơ/thời điểm cần thiết, không bảo đảm suất tái định cư.
- N08: Không xác nhận số hiệu không có chứng cứ hoặc 50 tỷ, nêu thiếu căn cứ.
