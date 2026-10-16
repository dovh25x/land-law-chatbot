# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-de584c31fc95f9a2`; fingerprint: `095725ee7c62d6f6100a8f224e57546750fd97a6d797ad842d518892d99fe52f`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Rà soát kỹ thuật có hỗ trợ AI theo đoạn nguồn và tiêu chí đã khóa; không phải thẩm định pháp lý độc lập.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 25.49 | True | pass |
| X02 | limited | 67.59 | Không áp dụng | fail |
| X03 | insufficient_evidence | 56.13 | True | fail |
| X04 | insufficient_evidence | 35.98 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 1 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 2 | 1 | 0 | 1 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 4, "deterministic": 0, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 185185 | 46055.0 | 67586 |
| token_usage | 4 | 47642 | 13104.0 | 14098 |
| llm_calls | 4 | 21 | 6.0 | 6 |
| tool_calls | 4 | 34 | 8.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Câu tự nhiên không nêu điều luật: dẫn đúng Điều 104, đủ tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc/dây chuyền; không thêm đơn giá.
- X02: Đạt trần 6 request trong khi retry/repair và xử lý quota; chưa có đáp án hoàn chỉnh. Không tính thông báo giới hạn là trả lời đạt. Chưa đủ bằng chứng rằng đã giải quyết sai phạm vi xuất hiện ở lượt cấu hình trước.
- X03: Chặn một phần claim nhưng phần còn lại tham chiếu đối tượng ở trên đã bị loại, chưa phân biệt rõ đối tượng khoản 1 với điều kiện khoản 2; chưa đáp ứng câu hỏi.
- X04: Không xác nhận số hiệu không có chứng cứ hoặc mức 50 tỷ, trả thiếu chứng cứ và không tạo điều khoản/quyền lợi. Hỏi thêm số hộ và nội dung quyết định là dữ kiện thừa; không dùng để tính tiền hay làm bằng chứng văn bản tồn tại.
