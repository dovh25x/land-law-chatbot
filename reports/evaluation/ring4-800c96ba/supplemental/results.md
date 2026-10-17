# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-581da76c79b0b362`; fingerprint: `800c96bad3ff018276b23b2ca1f49a0364c6e6b4d8eca3d4ff9f137bdafe4499`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 1 pass, 1 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Codex technical review against frozen criteria and corpus excerpts; AI-assisted, not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 8.96 | True | pass |
| X02 | limited | 45.77 | Không áp dụng | fail |
| X03 | insufficient_evidence | 49.78 | Không áp dụng | fail |
| X04 | insufficient_evidence | 28.09 | Không áp dụng | partial |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 1 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 2 | 0 | 1 | 1 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 4, "deterministic": 0, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 132596 | 36932.0 | 49777 |
| token_usage | 4 | 44785 | 11416.5 | 14489 |
| llm_calls | 4 | 20 | 5.5 | 6 |
| tool_calls | 4 | 34 | 8.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Câu tự nhiên tìm đúng Điều 104, phân biệt chi phí di chuyển và thiệt hại máy móc.
- X02: Hết ngân sách sáu request sau các lần provider giới hạn; không hoàn thành nội dung.
- X03: Chặn được mệnh đề phụ thuộc nhưng không trả được kết luận về điều kiện thay thế. Không coi abstention là task success.
- X04: Không xác nhận quyền lợi hoặc số tiền, nhưng lại yêu cầu nội dung văn bản chưa được chứng minh có trong corpus; bản sửa sau run đã thay bằng thông báo thiếu nguồn.

Corpus đa dự án cũ đã bị thu hồi asset nguồn. Báo cáo này dùng corpus Vành đai 4 mới; các báo cáo lịch sử của corpus cũ giữ nguyên checksum nhưng khả năng tái lập bị giới hạn. Xem `reports/corpus-retirement.json`.

Corpus đa dự án cũ đã bị thu hồi asset nguồn. Báo cáo này dùng corpus Vành đai 4 mới; các báo cáo lịch sử của corpus cũ giữ nguyên checksum nhưng khả năng tái lập bị giới hạn. Xem `reports/corpus-retirement.json`.
