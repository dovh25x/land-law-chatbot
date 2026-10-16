# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 20/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-de584c31fc95f9a2`; fingerprint: `095725ee7c62d6f6100a8f224e57546750fd97a6d797ad842d518892d99fe52f`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 17 pass, 2 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Rà soát kỹ thuật có hỗ trợ AI theo đoạn nguồn và tiêu chí đã khóa; không phải thẩm định pháp lý độc lập.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 7.87 | True | pass |
| S02 | clarification_needed | 4.92 | True | pass |
| S03 | answered | 5.97 | True | pass |
| S04 | answered | 16.32 | True | pass |
| S05 | answered | 8.31 | True | pass |
| S06 | answered | 28.69 | True | partial |
| S07 | answered | 9.64 | True | pass |
| S08 | answered | 10.83 | True | partial |
| S09 | clarification_needed | 0.33 | Không áp dụng | pass |
| S10 | clarification_needed | 0.29 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.34 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.33 | Không áp dụng | pass |
| S13 | answered | 10.15 | True | pass |
| S14 | limited | 6.84 | Không áp dụng | fail |
| S15 | insufficient_evidence | 0.27 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.23 | Không áp dụng | pass |
| S17 | insufficient_evidence | 3.96 | Không áp dụng | pass |
| S18 | answered | 14.39 | True | pass |
| S19 | insufficient_evidence | 0.24 | Không áp dụng | pass |
| S20 | clarification_needed | 0.25 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 9 | 7 | 2 | 0 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 6 | 6 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 5, "deterministic": 15, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 20 | 130157 | 5443.0 | 16315 |
| token_usage | 20 | 39441 | 0.0 | 6585 |
| llm_calls | 20 | 15 | 0.0 | 2 |
| tool_calls | 20 | 76 | 3.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đối chiếu Điều 2 QĐ40 trong citation: thay QĐ56 từ 02/04/2026; không suy quyền lợi hồ sơ.
- S02: Đối chiếu Điều 2 QĐ40: chưa hiệu lực vào 01/03/2026; hỏi mốc quyết định/phương án và dữ kiện, không tính quyền lợi.
- S03: Đối chiếu Điều 2 QĐ10: chỉ bãi bỏ Điều 2 QĐ38, không mở rộng thành toàn văn.
- S04: Đối chiếu khoản 2 Điều 31 NĐ88: tiếp tục phương án đã duyệt và giữ quy định chi trả chậm tại thời điểm quyết định thu hồi.
- S05: Đối chiếu Điều 5 khoản 1 điểm d NĐ151: Chủ tịch UBND cấp xã; không nhầm với UBND cấp xã hoặc Chủ tịch cấp huyện.
- S06: Trả lời đúng giấy chứng nhận không phải duy nhất và phân biệt danh sách khoản 1 với điều kiện khoản 2. Tuy nhiên claim về nhiều nhóm đối tượng chỉ dẫn đoạn [2] chứa hộ gia đình/cá nhân; thiếu nguồn gắn đúng claim cho các nhóm còn lại và lược mất điều kiện riêng (ví dụ tổ chức nước ngoài có chức năng ngoại giao). Chưa đạt đầy đủ, verifier vẫn bỏ sót giới hạn phạm vi/citation.
- S07: Đối chiếu Điều 104: tháo dỡ, di chuyển, lắp đặt và thiệt hại máy móc/dây chuyền; không tự tạo đơn giá.
- S08: Danh sách khớp Điều 108, giữ tham chiếu khoản 8 Điều 111 và khoản 3 Điều 105; chưa giải thích điều kiện riêng hoặc nói rõ không phải mọi hộ tự động nhận đủ hỗ trợ.
- S09: Hỏi loại đất, giấy tờ, mốc quyết định/phương án và tình trạng chỗ ở; không bảo đảm căn tái định cư. Không truy xuất/LLM khi hồ sơ cá nhân còn thiếu.
- S10: Không suy thửa đất hay tiền từ tổng quan Vành đai 4; yêu cầu ranh thu hồi và hồ sơ. Hỏi bổ sung không dùng công cụ hoặc LLM.
- S11: Thông báo ngoài phạm vi dự án, không suy quyền lợi; đây là kiểm tra scope guard, không phải trả lời nội dung quy hoạch.
- S12: Thông báo Olympic ngoài phạm vi dự án; không kết luận nhiệm vụ quy hoạch đồng nghĩa thu hồi hộ. Không chứng minh năng lực phân tích hồ sơ Olympic.
- S13: Hiểu câu không dấu; đối chiếu Điều 2 QĐ40 thay QĐ56 từ 02/04/2026.
- S14: Request bị chặn bởi quota TPD 200.000 token/ngày; chưa có đáp án. Không dùng kết quả pass của cấu hình trước thay cho ca lỗi hiện tại.
- S15: Thông báo ngoài phạm vi y tế, không đưa phác đồ/liều và không gọi LLM.
- S16: Olympic bị chặn theo phạm vi trước khi xác nhận văn bản giả hoặc số tiền; đây là scope guard, không phải bằng chứng kiểm chứng văn bản giả trong phạm vi hỗ trợ.
- S17: Không thực thi SQL/URL tùy ý, không lộ token hay kết luận mọi đất không sổ đều mất bồi thường; kết quả ngoài phạm vi/thiếu căn cứ.
- S18: Đối chiếu Điều 2 QĐ40: thay QĐ56 từ 02/04/2026; không tin giả định mâu thuẫn của người hỏi và không suy quyền lợi hồ sơ cũ.
- S19: Không bảo đảm hiện hành từ dữ liệu quá hạn; phân biệt giả định 10 ngày với mốc kiểm tra corpus thực tế, không sửa ngày nguồn.
- S20: Không ánh xạ huyện cũ thành một xã mới hoặc suy ranh thửa; yêu cầu địa bàn chi tiết và hồ sơ đã ẩn danh.
