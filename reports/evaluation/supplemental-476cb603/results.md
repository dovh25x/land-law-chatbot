# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 4/4 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-de584c31fc95f9a2`; fingerprint: `476cb6033b4eff9f842129a608b2d5025ca8830fe61ddfddaee2d7a7de934b6e`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 0 pass, 1 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI-assisted technical review against corpus excerpts and frozen criteria; not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| X01 | limited | 71.68 | Không áp dụng | fail |
| X02 | answered | 55.33 | True | fail |
| X03 | answered | 50.12 | True | partial |
| X04 | limited | 73.42 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 2 | 0 | 1 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 0 | 0 | 0 | 0 | 0 |
| execution_failure | 2 | 0 | 0 | 2 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Nguồn đáp án: {"llm": 3, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 4 | 250541 | 63502.5 | 73416 |
| token_usage | 4 | 31304 | 8721.0 | 13862 |
| llm_calls | 4 | 18 | 4.5 | 5 |
| tool_calls | 4 | 39 | 11.0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- X01: Lỗi thực thi do quota TPM và structured output; không hoàn tất câu trả lời. Không tính thông báo quota là trả lời đạt.
- X02: Trả lời riêng hỗ trợ chuyển đổi nghề tại Điều 109 thay vì các nhóm hỗ trợ Điều 108, nêu mức tiền ngoài yêu cầu và suy rộng người không thuộc nhóm này không nhận hỗ trợ. Verifier chưa chặn được sai phạm vi này.
- X03: Có điều kiện thay thế giấy chứng nhận và giới hạn nhóm khoản 1, nhưng vẫn gọi các giấy tờ/điều kiện khoản 2 là đối tượng; chưa phân biệt thuật ngữ rõ như câu hỏi yêu cầu.
- X04: Lỗi thực thi do quota TPM trước khi có đáp án hoàn chỉnh; không phát kết luận về văn bản giả/số tiền nhưng chưa đạt yêu cầu chức năng.
