# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-caf3c0833096ea4e`; fingerprint: `ce30e830008a2e8997f20501dd3f0c1a9c1981d08afcc71a0ba2aaee2cb84312`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 4 pass, 0 partial, 4 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering review against frozen rubric and cited source excerpts; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 10.91 | True | pass |
| N02 | insufficient_evidence | 45.98 | Không áp dụng | fail |
| N03 | insufficient_evidence | 2.96 | Không áp dụng | fail |
| N04 | limited | 30.13 | Không áp dụng | fail |
| N05 | answered | 14.39 | True | pass |
| N06 | insufficient_evidence | 15.42 | Không áp dụng | fail |
| N07 | clarification_needed | 0.03 | Không áp dụng | pass |
| N08 | insufficient_evidence | 0.03 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 2 | 0 | 0 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 4 | 1 | 0 | 3 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 119857 | 12649.5 | 45983 |
| token_usage | 8 | 58380 | 9044.5 | 13747 |
| llm_calls | 8 | 27 | 3.5 | 6 |
| tool_calls | 8 | 62 | 10.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí di chuyển và thiệt hại máy móc, không cam kết mức tiền.
- N02: Không trả lời được điều kiện hỗ trợ ổn định đời sống; abstain không tính là đúng nội dung.
- N03: Không trả lời được quy định chuyển nghề/tìm việc; không tính abstain là pass.
- N04: Giới hạn sáu request bị tiêu bởi quota/retry; giữ failure trong mẫu.
- N05: Đúng UBND cấp tỉnh theo khoản 2 Điều 104.
- N06: Raw retrieval đã thấy nguồn thay thế, nhưng agent chưa phát được kết luận đủ phạm vi. Không coi raw recall là chất lượng answer.
- N07: Không bảo đảm suất tái định cư, yêu cầu điều kiện/hồ sơ/thời điểm.
- N08: Không xác nhận văn bản giả hoặc khoản tiền, không suy sự tồn tại từ corpus.
