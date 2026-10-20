# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 4/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `3d6e1faf62189d31241ca80302db8ba768073e3185cd0934bfe6217e8e043cea`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 1 pass, 0 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 18.05 | True | pass |
| N02 | insufficient_evidence | 16.68 | Không áp dụng | fail |
| N03 | answered | 15.26 | True | fail |
| N04 | answered | 14.77 | True | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 3 | 1 | 0 | 2 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 1 | 0 | 0 | 1 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 4, "deterministic": 0, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 64754 | 15969.0 | 18051 |
| token_usage | 4 | 25759 | 6378.0 | 7805 |
| llm_calls | 4 | 8 | 2.0 | 2 |
| tool_calls | 4 | 29 | 7.5 | 11 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Chi phí di chuyển và thiệt hại máy móc được giải thích đúng phạm vi Điều104; không thêm checklist hoặc số tiền.
- N02: Abstention do diễn giải chỉ áp dụng cho nhóm đủ điều kiện trong khi nguồn còn nhánh khác; chưa đạt tác vụ có nguồn.
- N03: Claim đã phát hành mất điều kiện đã được bồi thường bằng tiền trong ví dụ đối tượng khoản1 Điều109; dẫn khoản1 không cứu phần giải thích sai phạm vi.
- N04: Claim đã phát hành thay hoàn thành bố trí tái định cư bằng phê duyệt phương án bố trí; ghép nghĩa vụ hỗ trợ với tình huống chưa có chỗ ở mới không được nguồn xác lập.
