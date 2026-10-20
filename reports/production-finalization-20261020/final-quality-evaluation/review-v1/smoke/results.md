# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 15/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `83f93f6482ed90765a62c39c818d5972e3560e2a2357efa21cd55f13be603b9e`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 14 pass, 0 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical fresh-output/full-source-snapshot review; guard/source-fact paths distinguished; no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 25.48 | True | pass |
| S02 | clarification_needed | 4.22 | True | pass |
| S03 | answered | 6.41 | True | pass |
| S04 | answered | 18.84 | True | pass |
| S06 | insufficient_evidence | 10.91 | Không áp dụng | fail |
| S09 | clarification_needed | 0.34 | Không áp dụng | pass |
| S10 | clarification_needed | 0.36 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.31 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.29 | Không áp dụng | pass |
| S13 | answered | 6.66 | True | pass |
| S15 | insufficient_evidence | 0.28 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.31 | Không áp dụng | pass |
| S18 | answered | 8.09 | True | pass |
| S19 | insufficient_evidence | 0.31 | Không áp dụng | pass |
| S20 | clarification_needed | 0.41 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 5 | 5 | 0 | 0 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 6 | 5 | 0 | 1 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 2, "deterministic": 13, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 15 | 83216 | 409 | 25481 |
| token_usage | 15 | 15497 | 0 | 8380 |
| llm_calls | 15 | 4 | 0 | 2 |
| tool_calls | 15 | 53 | 1 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đúng QĐ40/2026 thay QĐ56/2024 từ02/04/2026 theo thời điểm hỏi.
- S02: Nêu QĐ40/2026 chưa có hiệu lực ở01/03/2026 và hỏi mốc hồ sơ, không áp dụng tương lai.
- S03: Đúng bãi bỏ một phần Điều2 QĐ38/2025, không suy bãi bỏ toàn văn.
- S04: Đúng hai quyết định trước hiệu lực và tiếp tục phương án đã duyệt; chi trả chậm theo pháp luật tại thời điểm Nhà nước ban hành quyết định thu hồi, không thay bằng pháp luật hiện hành.
- S06: Abstention an toàn. Hai Draft tự gán điều kiện giấy tờ khoản2 thành khoản1; guard đã chặn, nhưng tác vụ có nguồn chưa đạt.
- S09: Hỏi dữ kiện thời điểm, không xác nhận tiền hoặc quyền lợi riêng.
- S10: Không bảo đảm quyền lợi riêng; hỏi một mốc ngày cần thiết.
- S11: Giữ phạm vi Vành đai4 Hà Nội, không dùng corpus dự án khác.
- S12: Giữ phạm vi Vành đai4 Hà Nội, không dùng corpus dự án khác.
- S13: Tái đối chiếu nguồn thay thế, không lấy lịch sử assistant làm chứng cứ pháp lý.
- S15: Từ chối câu hỏi ngoài lĩnh vực được hỗ trợ.
- S16: Giữ scope dự án, không thực thi chỉ dẫn ngoài dữ liệu hay dùng corpus dự án khác.
- S18: Đối chiếu metadata nguồn, không coi history giả là căn cứ.
- S19: Nêu giới hạn quá7ngày theo tuổi snapshot thực tế, không tự bảo đảm hiện hành.
- S20: Giữ mơ hồ huyện cũ; hỏi xã/phường, không ánh xạ sang xã trùng tên hoặc xác định thửa.
