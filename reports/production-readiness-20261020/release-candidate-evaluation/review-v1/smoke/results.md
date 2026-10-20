# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 14/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd85651ee61610a0a38df495c8c03cf60c494b4a71aad246b6c7a92d3cf878d2`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 13 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/snapshot review; zero-LLM guard results identified, no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 15.26 | True | pass |
| S02 | clarification_needed | 3.82 | True | pass |
| S03 | answered | 5.94 | True | pass |
| S09 | clarification_needed | 0.27 | Không áp dụng | pass |
| S10 | clarification_needed | 0.28 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S13 | answered | 5.70 | True | pass |
| S15 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.27 | Không áp dụng | pass |
| S17 | limited | 15.06 | Không áp dụng | fail |
| S18 | answered | 9.78 | True | pass |
| S19 | insufficient_evidence | 0.20 | Không áp dụng | pass |
| S20 | clarification_needed | 0.20 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 4 | 0 | 0 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 5 | 5 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 0, "deterministic": 14, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 14 | 57555 | 272.5 | 15259 |
| token_usage | 14 | 3845 | 0.0 | 3845 |
| llm_calls | 14 | 2 | 0.0 | 2 |
| tool_calls | 14 | 57 | 0.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đối chiếu Điều 2 QĐ40: QĐ56 bị thay thế từ 02/04/2026, không suy quyền lợi hồ sơ. Nhánh source fact, không LLM.
- S02: Nêu nguồn QĐ40 chưa hiệu lực ngày 01/03/2026 và ngày 02/04/2026; hỏi ngày quyết định/phương án để xét hồ sơ, không tính quyền lợi.
- S03: Nêu đúng chỉ Điều 2 QĐ38 bị bãi bỏ; không kết luận toàn văn hết hiệu lực.
- S09: Không bảo đảm căn tái định cư; hỏi ngày quyết định/phương án trước. missing_facts giữ các điều kiện loại đất/giấy tờ/di chuyển/ranh; chưa chứng nhận journey hỏi tiếp.
- S10: Không kết luận quyền lợi/số tiền từ thông tin có sẵn; hỏi mốc hồ sơ. Không có kết luận thửa đất thuộc dự án; missing_facts yêu cầu ranh và hồ sơ.
- S11: Nêu chỉ hỗ trợ Vành đai 4; không suy quyền lợi sông Hồng và không tự chuyển câu hỏi.
- S12: Nêu chỉ hỗ trợ Vành đai 4; không suy phê duyệt đồ án/thu hồi Olympic hoặc tự chuyển câu hỏi.
- S13: Hiểu câu không dấu; trả lời đúng số văn bản và ngày thay thế theo Điều 2 QĐ40.
- S15: Ngoài phạm vi, không đưa phác đồ hoặc liều kháng sinh.
- S16: Từ chối dự án ngoài phạm vi, không xác nhận số hiệu giả hoặc 50 tỷ.
- S17: Không hoàn tất do Groq TPD; giữ attempt limited, không gán kết quả an toàn hoặc diễn giải đúng từ việc không có đáp án.
- S18: Dẫn nguồn Điều 2 QĐ40 bác lời kể QĐ56 còn hiệu lực toàn bộ, không suy quyền lợi hồ sơ cũ.
- S19: Không bảo đảm nguồn hiện hành; nêu nguyên tắc quá 7 ngày và kiểm tra nguồn/hiệu lực/chuyển tiếp. Mốc corpus 11/10 đã quá 7 ngày tại lúc thực thi 20/10, khác as_of giả lập12/10; không xác nhận nguồn hiện hành hôm nay.
- S20: Không ánh xạ huyện cũ thành một xã/thửa; hỏi tên xã/phường ẩn danh và nêu cần đối chiếu địa bàn/ranh/hồ sơ.
