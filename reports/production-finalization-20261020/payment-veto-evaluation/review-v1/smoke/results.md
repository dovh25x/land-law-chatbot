# Kết quả đánh giá hệ thống

Trạng thái: **partial**. Đã chạy 13/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-a26bc99e541fbbe2`; fingerprint: `aab575603c781a942e306bc6c17cba0d3b1f3e307e75d530b973fdc33fa527b1`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 13 pass, 0 partial, 0 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: AI technical fresh-output/full-source-snapshot review; guard/source-fact paths distinguished; no independent legal certification.

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 17.47 | True | pass |
| S02 | clarification_needed | 4.31 | True | pass |
| S03 | answered | 6.76 | True | pass |
| S09 | clarification_needed | 0.31 | Không áp dụng | pass |
| S10 | clarification_needed | 0.31 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.31 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.36 | Không áp dụng | pass |
| S13 | answered | 6.55 | True | pass |
| S15 | insufficient_evidence | 0.41 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.41 | Không áp dụng | pass |
| S18 | answered | 8.05 | True | pass |
| S19 | insufficient_evidence | 0.36 | Không áp dụng | pass |
| S20 | clarification_needed | 0.42 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 4 | 4 | 0 | 0 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 5 | 5 | 0 | 0 | 0 |
| execution_failure | 0 | 0 | 0 | 0 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 0, "deterministic": 13, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 13 | 46024 | 409 | 17466 |
| token_usage | 13 | 0 | 0 | 0 |
| llm_calls | 13 | 0 | 0 | 0 |
| tool_calls | 13 | 46 | 0 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Đúng QĐ40/2026 thay QĐ56/2024 từ02/04/2026 theo thời điểm hỏi.
- S02: Nêu QĐ40/2026 chưa có hiệu lực ở01/03/2026 và hỏi mốc hồ sơ, không áp dụng tương lai.
- S03: Đúng bãi bỏ một phần Điều2 QĐ38/2025, không suy bãi bỏ toàn văn.
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
