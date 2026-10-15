# Kết quả 20 ca trên API cloud

Trạng thái: **partial**. Đã chạy 16/20. Chưa tự động chấm đúng pháp lý.

| Ca | Trạng thái API | Giây | Trích dẫn khớp nguồn | Review nội dung |
|---|---|---:|---|---|
| S01 | answered | 23.69 | True | pass |
| S02 | clarification_needed | 8.19 | True | pass |
| S03 | answered | 11.63 | True | pass |
| S04 | answered | 15.07 | True | pass |
| S05 | answered | 20.14 | True | pass |
| S06 | answered | 12.75 | True | partial |
| S07 | answered | 17.32 | True | pass |
| S08 | answered | 14.14 | True | pass |
| S09 | clarification_needed | 9.42 | True | pass |
| S10 | clarification_needed | 12.55 | True | pass |
| S11 | clarification_needed | 8.22 | True | pass |
| S12 | insufficient_evidence | 36.85 | True | fail |
| S13 | answered | 9.79 | True | pass |
| S14 | insufficient_evidence | 24.1 | True | fail |
| S15 | insufficient_evidence | 6.61 | True | pass |
| S16 | insufficient_evidence | 32.85 | True | partial |

Phạm vi: API công khai, một người dùng, có thể gồm cold start. Không phải p95/SLA; không ghép báo cáo cấu hình khác.
Câu tiếp nối S14 dùng câu trả lời thật của lượt mở đầu cùng phiên; không chèn lịch sử giả.

## Ghi chú rà soát kỹ thuật (không phải thẩm định pháp lý độc lập)
- S01: Nêu QĐ56 hết hiệu lực và QĐ40 thay thế từ 02/04/2026; đối chiếu Điều 2 trong đoạn nguồn.
- S02: Không áp QĐ40 trước ngày hiệu lực, hỏi thêm ngày quyết định/phương án thay vì tính quyền lợi.
- S03: Phân biệt bãi bỏ Điều 2 với bãi bỏ toàn bộ QĐ38; dẫn Điều 2 QĐ10.
- S04: Đáp án bám quy định chuyển tiếp về phương án đã phê duyệt và xử lý chi trả chậm trong Điều 31.
- S05: Nêu Chủ tịch UBND cấp xã thực hiện thẩm quyền; trích Điều 5, không khái quát mọi thẩm quyền.
- S06: Nêu điều kiện thay thế giấy chứng nhận và giới hạn khoản 1, nhưng danh sách chỉ a/b có thể bị hiểu là đầy đủ; cần nêu đây là ví dụ hoặc liệt kê đủ.
- S07: Các chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc bám Điều 104.
- S08: Nêu đủ sáu nhóm hỗ trợ và điều kiện dẫn chiếu trong Điều 108.
- S09: Hỏi giấy tờ, loại đất, thời điểm, nhu cầu di chuyển; không hứa suất tái định cư.
- S10: Không suy quyền lợi/thửa đất từ tổng quan Vành đai 4; hỏi hồ sơ và ranh thu hồi.
- S11: Không khẳng định quyền lợi từ thông tin dự án sông Hồng; cần dữ kiện và hồ sơ. Đáp án còn chung chung.
- S12: Không suy đoán thu hồi từng hộ nhưng không phân biệt được nhiệm vụ quy hoạch với phê duyệt đồ án; hỏi lại tài liệu đã có thay vì trả lời quy tắc chung.
- S13: Câu không dấu vẫn nêu đúng mốc thay thế QĐ56/QĐ40 và nguồn Điều 2.
- S14: Cùng phiên đã hỏi QĐ40, nhưng lượt tiếp nối không giải tham chiếu văn bản đó; cần nêu rõ số văn bản khi demo.
- S15: Từ chối câu y tế ngoài phạm vi, không đưa phác đồ.
- S16: Không xác nhận số tiền 50 tỷ, nhưng diễn đạt không có trong bất kỳ văn bản nào quá rộng so với corpus snapshot; nên nói chưa tìm thấy căn cứ trong nguồn đã kiểm tra.

Trở ngại: ValueError: Public daily/provider limit: resume checkpoint later
