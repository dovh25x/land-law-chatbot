# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 14/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `4e8dd8d2b56789bfb2496f5c7b475162f2631813615f6289a1d8ab1a509a85e7`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 10 pass, 2 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full cited corpus passages; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 6.16 | True | pass |
| S02 | clarification_needed | 3.79 | True | pass |
| S03 | answered | 5.12 | True | pass |
| S04 | answered | 11.06 | True | partial |
| S05 | answered | 6.75 | True | pass |
| S06 | insufficient_evidence | 5.94 | Không áp dụng | fail |
| S07 | answered | 6.48 | True | pass |
| S08 | answered | 6.15 | True | partial |
| S09 | clarification_needed | 0.23 | Không áp dụng | pass |
| S10 | clarification_needed | 0.22 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.24 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.34 | Không áp dụng | pass |
| S13 | answered | 7.25 | True | pass |
| S14 | limited | 5.74 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 7 | 5 | 2 | 0 | 0 |
| clarification | 3 | 3 | 0 | 0 | 0 |
| insufficient | 3 | 2 | 0 | 1 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 5, "deterministic": 9, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 14 | 65467 | 5837.0 | 11061 |
| token_usage | 14 | 27025 | 0.0 | 7183 |
| llm_calls | 14 | 11 | 0.0 | 2 |
| tool_calls | 14 | 51 | 2.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đối chiếu đúng Điều 2 QĐ40 và mốc 02/04/2026; chỉ nêu tình trạng hiệu lực, không suy quyền lợi cụ thể.
- S02: Không áp QĐ40 cho 01/03/2026; hỏi ngày quyết định/phương án và giấy tờ, yêu cầu đối chiếu chuyển tiếp, không tính tiền.
- S03: Chỉ Điều 2 QĐ38 bị bãi bỏ; không đánh đồng toàn văn hết hiệu lực.
- S04: Đúng nhánh khoản 2 Điều 31: đã thu hồi và phê duyệt trước hiệu lực thì tiếp tục phương án; thiếu quy định xử lý chậm chi trả trong cùng khoản mà rubric đã khóa yêu cầu.
- S05: Đúng Chủ tịch UBND cấp xã theo điểm d khoản 1 Điều 5 NĐ151 tại ngày hỏi; không áp sửa đổi tương lai.
- S06: Từ chối thay vì phân biệt đối tượng khoản 1 và các điều kiện thay thế khoản 2 Điều 95. Không biến safe abstention thành content pass.
- S07: Nêu đủ tháo dỡ, di chuyển, lắp đặt và thiệt hại máy móc/dây chuyền trong quá trình đó, không tạo đơn giá.
- S08: Liệt kê đúng các nhóm khoản 1 Điều 108 và hai dẫn chiếu, nhưng thiếu phân biệt điều kiện áp dụng riêng, chưa đạt toàn bộ rubric.
- S09: Hỏi loại đất/giấy tờ/chuyển chỗ ở/hồ sơ/thời điểm, không bảo đảm căn tái định cư.
- S10: Không xác định thửa hoặc tiền từ tin tổng quan; yêu cầu ranh thu hồi và hồ sơ.
- S11: Giữ phạm vi Vành đai 4, không kết luận quyền lợi dự án sông Hồng.
- S12: Giữ phạm vi Vành đai 4, không suy thu hồi/đồ án từ dự án Olympic.
- S13: Hiểu không dấu, nêu đúng QĐ40 thay QĐ56 và mốc thời gian.
- S14: Lượt thực thi bị Groq TPD giới hạn; chưa có câu trả lời kiểm chứng. Giữ nguyên attempt, không coi là content pass.
