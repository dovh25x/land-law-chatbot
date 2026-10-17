# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 8/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-581da76c79b0b362`; fingerprint: `800c96bad3ff018276b23b2ca1f49a0364c6e6b4d8eca3d4ff9f137bdafe4499`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 1 partial, 5 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Codex technical review against frozen criteria and corpus excerpts; AI-assisted, not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | limited | 2.98 | Không áp dụng | fail |
| N02 | answered | 14.14 | True | partial |
| N03 | answered | 11.95 | True | fail |
| N04 | answered | 7.21 | True | fail |
| N05 | answered | 3.80 | True | pass |
| N06 | limited | 38.70 | Không áp dụng | fail |
| N07 | clarification_needed | 0.03 | Không áp dụng | pass |
| N08 | limited | 51.94 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 1 | 1 | 2 | 0 |
| clarification | 1 | 1 | 0 | 0 | 0 |
| insufficient | 0 | 0 | 0 | 0 | 0 |
| execution_failure | 3 | 0 | 0 | 3 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 2, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 8 | 130747 | 9578.5 | 51942 |
| token_usage | 8 | 62154 | 8752.5 | 13910 |
| llm_calls | 8 | 28 | 4.0 | 6 |
| tool_calls | 8 | 57 | 8.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Provider TPM chặn ngay planner; chưa trả được quy định.
- N02: Nêu tỷ lệ/thời gian theo Điều 19 NĐ88 nhưng chưa bao quát nhánh dưới 30%; không xác nhận quyền lợi cá nhân.
- N03: Bỏ điều kiện quan trọng của Điều 109: bảng giá đất, giới hạn diện tích/hạn mức và ngoại lệ với một số đối tượng nhận giao khoán. Citation khớp không chứng minh diễn giải đầy đủ.
- N04: Sai trọng tâm và phạm vi: dùng hỗ trợ tự lo chỗ ở/kinh phí tổ chức thay nguyên tắc bố trí tái định cư trước thu hồi; runtime verifier đã bỏ lọt. Bản sửa sau run thêm lớp chặn, chưa tái đánh giá LLM do TPD.
- N05: Đúng UBND cấp tỉnh theo khoản 2 Điều 104.
- N06: Hết ngân sách thực thi; chưa cung cấp được văn bản thay thế.
- N07: Yêu cầu hồ sơ và không xác nhận chắc chắn suất tái định cư.
- N08: Hết ngân sách, chưa nêu thiếu căn cứ một cách phù hợp. Bản sửa sau run xử lý viện dẫn chưa biết theo quy tắc, không gọi LLM.

Corpus đa dự án cũ đã bị thu hồi asset nguồn. Báo cáo này dùng corpus Vành đai 4 mới; các báo cáo lịch sử của corpus cũ giữ nguyên checksum nhưng khả năng tái lập bị giới hạn. Xem `reports/corpus-retirement.json`.

Corpus đa dự án cũ đã bị thu hồi asset nguồn. Báo cáo này dùng corpus Vành đai 4 mới; các báo cáo lịch sử của corpus cũ giữ nguyên checksum nhưng khả năng tái lập bị giới hạn. Xem `reports/corpus-retirement.json`.
