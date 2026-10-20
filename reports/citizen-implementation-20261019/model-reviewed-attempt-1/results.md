# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 3/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `e55d2a3d2e59e9564d8cdad04c3d2575ecba4ebfe173876428e79a689b3e779e`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 0 pass, 0 partial, 3 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Implementation-agent technical review of frozen rubric, actual source excerpts and execution trace; not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | limited | 65.56 | Không áp dụng | fail |
| N02 | answered | 10.65 | True | fail |
| N03 | limited | 11.17 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 1 | 0 | 0 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 0 | 0 | 0 | 0 | 0 |
| execution_failure | 2 | 0 | 0 | 2 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 2, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 3 | 87375 | 11169 | 65555 |
| token_usage | 3 | 13968 | 6352 | 7616 |
| llm_calls | 3 | 6 | 2 | 3 |
| tool_calls | 3 | 18 | 7 | 8 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Không hoàn tất câu trả lời. Verifier phát hiện claim về máy móc trích Điều 102 thay nguồn Điều 104, rồi lượt repair gặp TPM. Không có kết luận chưa verify được phát; lỗi thực thi vẫn là fail tác vụ.
- N02: Runtime trả answered và citation khớp nguồn, nhưng diễn giải định mức thiếu điều kiện đủ điều kiện bồi thường về đất và đơn vị cho một nhân khẩu; có tham chiếu (a)-(e) không được định nghĩa. Regression tái hiện cho thấy verifier giả lập đồng ý vẫn để lọt. Cần veto trước phát; không sửa verdict thành pass sau khi sửa code.
- N03: Groq giới hạn TPD trước khi có generation hoàn tất. Giữ limited trong mẫu số; không đổi thành ca từ chối đúng.
