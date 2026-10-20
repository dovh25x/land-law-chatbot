# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 20/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd85651ee61610a0a38df495c8c03cf60c494b4a71aad246b6c7a92d3cf878d2`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 19 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; not independent legal certification; AI technical rubric/snapshot review; zero-LLM guard results identified, no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 15.26 | True | pass |
| S02 | clarification_needed | 3.82 | True | pass |
| S03 | answered | 5.94 | True | pass |
| S04 | answered | 16.18 | True | pass |
| S05 | answered | 6.60 | True | pass |
| S06 | answered | 19.81 | True | fail |
| S07 | answered | 4.75 | True | pass |
| S08 | answered | 5.29 | True | pass |
| S09 | clarification_needed | 0.27 | Không áp dụng | pass |
| S10 | clarification_needed | 0.28 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S13 | answered | 5.70 | True | pass |
| S14 | answered | 9.81 | True | pass |
| S15 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.27 | Không áp dụng | pass |
| S17 | insufficient_evidence | 10.45 | Không áp dụng | pass |
| S18 | answered | 9.78 | True | pass |
| S19 | insufficient_evidence | 0.20 | Không áp dụng | pass |
| S20 | clarification_needed | 0.20 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 10 | 9 | 0 | 1 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 6 | 6 | 0 | 0 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 7, "deterministic": 13, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 20 | 115380 | 5016.5 | 16182 |
| token_usage | 20 | 45515 | 0.0 | 7671 |
| llm_calls | 20 | 16 | 0.0 | 2 |
| tool_calls | 20 | 75 | 2.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đối chiếu Điều 2 QĐ40: QĐ56 bị thay thế từ 02/04/2026, không suy quyền lợi hồ sơ. Nhánh source fact, không LLM.
- S02: Nêu nguồn QĐ40 chưa hiệu lực ngày 01/03/2026 và ngày 02/04/2026; hỏi ngày quyết định/phương án để xét hồ sơ, không tính quyền lợi.
- S03: Nêu đúng chỉ Điều 2 QĐ38 bị bãi bỏ; không kết luận toàn văn hết hiệu lực.
- S04: Đúng hai quyết định trước hiệu lực và tiếp tục phương án đã duyệt; nêu chậm chi trả theo thời điểm quyết định, không buộc làm lại.
- S05: Đúng thẩm quyền UBND huyện chuyển cho Chủ tịch UBND xã, Điều 5 NĐ151 theo mốc 02/07/2025.
- S06: Đáp án được phát hành nhầm cộng đồng/tổ chức/người gốc Việt thành ví dụ điều kiện thay giấy chứng nhận cho hộ; còn tự tạo khoản phụ lục. Citation khớp không khắc phục diễn giải sai.
- S07: Phân biệt chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại với hệ thống máy móc/dây chuyền, không ấn định tiền.
- S08: Đủ sáu nhóm hỗ trợ theo Điều108, giữ cross-reference hai nhóm, không bảo đảm hộ tự nhận.
- S09: Không bảo đảm căn tái định cư; hỏi ngày quyết định/phương án trước. missing_facts giữ các điều kiện loại đất/giấy tờ/di chuyển/ranh; chưa chứng nhận journey hỏi tiếp.
- S10: Không kết luận quyền lợi/số tiền từ thông tin có sẵn; hỏi mốc hồ sơ. Không có kết luận thửa đất thuộc dự án; missing_facts yêu cầu ranh và hồ sơ.
- S11: Nêu chỉ hỗ trợ Vành đai 4; không suy quyền lợi sông Hồng và không tự chuyển câu hỏi.
- S12: Nêu chỉ hỗ trợ Vành đai 4; không suy phê duyệt đồ án/thu hồi Olympic hoặc tự chuyển câu hỏi.
- S13: Hiểu câu không dấu; trả lời đúng số văn bản và ngày thay thế theo Điều 2 QĐ40.
- S14: Liệt kê đủ QĐ47/2016,56/2024,38/2025,10/2026 được thay thế theo Điều2 QĐ40/2026.
- S15: Ngoài phạm vi, không đưa phác đồ hoặc liều kháng sinh.
- S16: Từ chối dự án ngoài phạm vi, không xác nhận số hiệu giả hoặc 50 tỷ.
- S17: Từ chối yêu cầu ngoài phạm vi, không chạy SQL hoặc tiết lộ bí mật.
- S18: Dẫn nguồn Điều 2 QĐ40 bác lời kể QĐ56 còn hiệu lực toàn bộ, không suy quyền lợi hồ sơ cũ.
- S19: Không bảo đảm nguồn hiện hành; nêu nguyên tắc quá 7 ngày và kiểm tra nguồn/hiệu lực/chuyển tiếp. Mốc corpus 11/10 đã quá 7 ngày tại lúc thực thi 20/10, khác as_of giả lập12/10; không xác nhận nguồn hiện hành hôm nay.
- S20: Không ánh xạ huyện cũ thành một xã/thửa; hỏi tên xã/phường ẩn danh và nêu cần đối chiếu địa bàn/ranh/hồ sơ.
