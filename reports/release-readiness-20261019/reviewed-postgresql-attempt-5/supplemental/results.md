# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `8db2d701d6d27b69f3cb01615c9a8a16ef3a3fe74fb7c117721f2349f2a523dc`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 2 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI engineering technical comparison against frozen rubric and full cited corpus passages; not independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | answered | 11.57 | True | pass |
| X02 | insufficient_evidence | 13.01 | Không áp dụng | fail |
| X03 | insufficient_evidence | 9.43 | Không áp dụng | fail |
| X04 | insufficient_evidence | 0.27 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 1 | 0 | 0 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 3 | 1 | 0 | 2 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 3, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 34276 | 10498.5 | 13005 |
| token_usage | 4 | 20953 | 6290.0 | 8373 |
| llm_calls | 4 | 6 | 2.0 | 2 |
| tool_calls | 4 | 12 | 3.5 | 5 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Đúng chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc/dây chuyền trong quá trình đó, không tạo mức tiền.
- X02: Verifier chặn draft/repair; không có giải thích được phát hành về nhóm hỗ trợ và điều kiện áp dụng, nên chưa đạt câu nội dung dù từ chối an toàn.
- X03: Không có câu trả lời được phát hành phân biệt đối tượng khoản 1 và điều kiện khoản 2 Điều 95; safe abstention không đạt rubric nội dung.
- X04: Không xác nhận văn bản giả hay mức 50 tỷ; nêu thiếu chứng cứ và không suy quyền lợi từ việc corpus không có số hiệu.
