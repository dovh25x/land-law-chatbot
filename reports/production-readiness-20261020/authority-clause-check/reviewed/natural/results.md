# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 6/8 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `cd7187c839ba7b388e38b2ee13c139c3e60288f13fb67b07039e08148552937a`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 2 pass, 0 partial, 4 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical rubric/source review; independent legal/user-research criteria waived by owner; not legal acceptance.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| N01 | answered | 17.81 | True | pass |
| N02 | insufficient_evidence | 18.36 | Không áp dụng | fail |
| N03 | insufficient_evidence | 11.58 | Không áp dụng | fail |
| N04 | answered | 18.75 | True | fail |
| N05 | answered | 13.17 | True | pass |
| N06 | limited | 9.64 | Không áp dụng | fail |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 3 | 2 | 0 | 1 | 0 |
| clarification | 0 | 0 | 0 | 0 | 0 |
| insufficient | 2 | 0 | 0 | 2 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 5, "deterministic": 1, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 6 | 89310 | 15488.0 | 18755 |
| token_usage | 6 | 36417 | 6707.5 | 8939 |
| llm_calls | 6 | 12 | 2.0 | 3 |
| tool_calls | 6 | 44 | 7.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- N01: Phân biệt chi phí di chuyển và thiệt hại tháo dỡ/vận chuyển/lắp đặt máy móc; không bảo đảm mức tiền. Đối chiếu Điều 104 snapshot.
- N02: Không trả lời được câu hỏi có căn cứ trong corpus; abstention giữ an toàn nhưng không đạt tác vụ.
- N03: Không trả lời được câu hỏi có nguồn trong corpus; abstention giữ an toàn nhưng không đạt tác vụ.
- N04: Biến tình huống chưa bố trí chỗ ở của người hỏi thành tiền đề pháp luật cho nhóm nghĩa vụ khác; mở rộng hình thức bồi thường mà thiếu chủ thể/điều kiện. Đã tái hiện regression; guard ở bản sau sẽ veto cả nhóm.
- N05: Nêu đúng UBND cấp tỉnh; citation toàn Điều 104 chứa khoản 2. Không bảo đảm mức tiền.
- N06: Không hoàn tất vì giới hạn TPD thật của Groq; giữ nguyên attempt và mẫu số, không gọi là pass hoặc lỗi diễn giải pháp luật.
