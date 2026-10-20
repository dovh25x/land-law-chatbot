# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 14/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e409d8ac39e2edf6cf9f039704fcd5cee7d377a583c787d004e4dd694c17ac02`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 13 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/full source snapshot review; no independent legal certification; limited/not_run retained in denominators.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 6.00 | True | pass |
| S02 | clarification_needed | 3.81 | True | pass |
| S03 | answered | 5.72 | True | pass |
| S04 | limited | 9.40 | Không áp dụng | fail |
| S09 | clarification_needed | 0.22 | Không áp dụng | pass |
| S10 | clarification_needed | 0.20 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.20 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.22 | Không áp dụng | pass |
| S13 | answered | 15.79 | True | pass |
| S15 | insufficient_evidence | 0.26 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.30 | Không áp dụng | pass |
| S18 | answered | 10.65 | True | pass |
| S19 | insufficient_evidence | 0.23 | Không áp dụng | pass |
| S20 | clarification_needed | 0.31 | Không áp dụng | pass |

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
| elapsed_ms | 14 | 53319 | 306.5 | 15793 |
| token_usage | 14 | 0 | 0.0 | 0 |
| llm_calls | 14 | 1 | 0.0 | 1 |
| tool_calls | 14 | 51 | 0.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đúng QĐ40/2026 thay QĐ56/2024 từ02/04/2026, theo thời điểm hỏi.
- S02: Nêu QĐ40/2026 chưa có hiệu lực tại01/03/2026 và hỏi mốc hồ sơ; không áp dụng tương lai.
- S03: Đúng bãi bỏ một phần Điều2 QĐ38/2025, không suy bãi bỏ toàn văn.
- S04: Limited do TPD200000. Giữ nguyên attempt, không coi là lỗi nội dung hoặc một đáp án đạt.
- S09: Không bảo đảm căn tái định cư; hỏi ngày quyết định/phương án trước. missing_facts giữ các điều kiện loại đất/giấy tờ/di chuyển/ranh; chưa chứng nhận journey hỏi tiếp.
- S10: Không kết luận quyền lợi/số tiền từ thông tin có sẵn; hỏi mốc hồ sơ. Không có kết luận thửa đất thuộc dự án; missing_facts yêu cầu ranh và hồ sơ.
- S11: Nêu chỉ hỗ trợ Vành đai 4; không suy quyền lợi sông Hồng và không tự chuyển câu hỏi.
- S12: Nêu chỉ hỗ trợ Vành đai 4; không suy phê duyệt đồ án/thu hồi Olympic hoặc tự chuyển câu hỏi.
- S13: Hiểu câu không dấu; trả lời đúng số văn bản và ngày thay thế theo Điều 2 QĐ40.
- S15: Ngoài phạm vi, không đưa phác đồ hoặc liều kháng sinh.
- S16: Từ chối dự án ngoài phạm vi, không xác nhận số hiệu giả hoặc 50 tỷ.
- S18: Dẫn nguồn Điều 2 QĐ40 bác lời kể QĐ56 còn hiệu lực toàn bộ, không suy quyền lợi hồ sơ cũ.
- S19: Không bảo đảm nguồn hiện hành; nêu nguyên tắc quá 7 ngày và kiểm tra nguồn/hiệu lực/chuyển tiếp. Mốc corpus 11/10 đã quá 7 ngày tại lúc thực thi 20/10, khác as_of giả lập12/10; không xác nhận nguồn hiện hành hôm nay.
- S20: Không ánh xạ huyện cũ thành một xã/thửa; hỏi tên xã/phường ẩn danh và nêu cần đối chiếu địa bàn/ranh/hồ sơ.
