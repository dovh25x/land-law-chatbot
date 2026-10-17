# Kết quả đánh giá hệ thống

Trạng thái: **reviewed**. Đã chạy 20/20 ca agentic.
Model: `openai/gpt-oss-120b`; release: `corpus-581da76c79b0b362`; fingerprint: `800c96bad3ff018276b23b2ca1f49a0364c6e6b4d8eca3d4ff9f137bdafe4499`.

**Cách chạy:** CLI gọi Groq thật trên corpus snapshot; HTTPS được kiểm chứng riêng. Lịch sử trong bộ kiểm tra là fixture cố định khi có.

Rà soát kỹ thuật theo tiêu chí/nguồn: 18 pass, 1 partial, 1 fail, 0 chưa rà soát.
Không phải thẩm định pháp lý độc lập. Ca không có trích dẫn không được tính là bằng chứng hỗ trợ kết luận.
Phương pháp rà soát: Codex technical review against frozen criteria and corpus excerpts; AI-assisted, not independent legal certification..

| Ca | Trạng thái | Giây | Trích dẫn khớp corpus | Rà soát |
|---|---|---:|---|---|
| S01 | answered | 8.92 | True | pass |
| S02 | clarification_needed | 7.36 | True | pass |
| S03 | answered | 8.44 | True | pass |
| S04 | answered | 8.51 | True | partial |
| S05 | answered | 2.60 | True | pass |
| S06 | limited | 45.68 | Không áp dụng | fail |
| S07 | answered | 2.86 | True | pass |
| S08 | answered | 2.68 | True | pass |
| S09 | clarification_needed | 0.01 | Không áp dụng | pass |
| S10 | clarification_needed | 0.01 | Không áp dụng | pass |
| S11 | insufficient_evidence | 0.02 | Không áp dụng | pass |
| S12 | insufficient_evidence | 0.01 | Không áp dụng | pass |
| S13 | answered | 6.35 | True | pass |
| S14 | answered | 7.27 | True | pass |
| S15 | insufficient_evidence | 0.02 | Không áp dụng | pass |
| S16 | insufficient_evidence | 0.02 | Không áp dụng | pass |
| S17 | insufficient_evidence | 2.46 | Không áp dụng | pass |
| S18 | answered | 15.34 | True | pass |
| S19 | insufficient_evidence | 0.02 | Không áp dụng | pass |
| S20 | clarification_needed | 0.09 | Không áp dụng | pass |

## Kết quả theo hành vi

| Nhóm | Số ca | Đạt | Một phần | Lỗi | Chưa rà soát |
|---|---:|---:|---:|---:|---:|
| answered | 9 | 8 | 1 | 0 | 0 |
| clarification | 4 | 4 | 0 | 0 | 0 |
| insufficient | 6 | 6 | 0 | 0 | 0 |
| execution_failure | 1 | 0 | 0 | 1 | 0 |

Số đạt của toàn bộ suite gồm cả hỏi lại và từ chối; không phải độ chính xác trả lời pháp luật.
Luồng xử lý (có bước sinh Draft bằng LLM, kể cả khi bị chặn sau kiểm chứng): {"llm": 6, "deterministic": 14, "unknown": 0}. unknown: artifact cũ không ghi nhận nguồn sinh.

## Thống kê lượt chạy

| Chỉ số | Số mẫu | Tổng | Median | p95 |
|---|---:|---:|---:|---:|
| elapsed_ms | 20 | 118688 | 2638.5 | 15343 |
| token_usage | 20 | 42553 | 0.0 | 6607 |
| llm_calls | 20 | 17 | 0.0 | 2 |
| tool_calls | 20 | 76 | 3.5 | 12 |

Thống kê mô tả một lượt chạy CLI, không phải SLA. Khớp citation chỉ xác nhận nguồn gốc, không chứng minh diễn giải đúng.

## Ghi chú từng ca
- S01: Điều 2 QĐ40 chứng minh thay thế QĐ56 từ 02/04/2026; không suy quyền lợi riêng.
- S02: Nêu đúng QĐ40 chưa hiệu lực tại ngày hỏi và yêu cầu hồ sơ; không tính quyền lợi.
- S03: Giữ đúng phạm vi bãi bỏ riêng Điều 2 QĐ38.
- S04: Điều kiện chuyển tiếp và chi trả chậm được giữ; cách gọi người thu hồi chưa rõ chủ thể và cần diễn đạt chính xác hơn.
- S05: Nguồn Điều 5 NĐ151 tại thời điểm hỏi chứng minh Chủ tịch UBND cấp xã, không nhầm UBND.
- S06: Không có đáp án nội dung; sáu request gồm retry trong giới hạn TPM dẫn tới hết ngân sách. Không tính việc chặn kết luận sai là hoàn thành câu hỏi.
- S07: Nêu chi phí tháo dỡ/di chuyển/lắp đặt và thiệt hại máy móc theo nguồn; không tạo đơn giá.
- S08: Liệt kê nhóm hỗ trợ và giới hạn không tự động hưởng tất cả; không giải thích dẫn chiếu thiếu nguồn.
- S09: Hỏi hồ sơ/thời điểm/điều kiện; không bảo đảm căn tái định cư.
- S10: Không suy thửa đất hoặc tiền từ tổng quan, yêu cầu ranh và hồ sơ.
- S11: Từ chối dự án ngoài phạm vi mới. Tiêu chí cũ nhắc nguồn tham khảo trong thư viện đã được quyết định một dự án thay thế, không giữ dữ liệu dự án khác.
- S12: Từ chối Olympic, không suy quyền lợi. Đánh giá theo phạm vi một dự án đã chốt; không yêu cầu giữ nguồn ngoài phạm vi như câu chữ cũ.
- S13: Hiểu không dấu, dẫn QĐ40 thay QĐ56 đúng ngày.
- S14: Giải tham chiếu fixture QĐ40; danh sách bốn quyết định khớp Điều 2.
- S15: Không đưa hướng dẫn y tế ngoài phạm vi.
- S16: Từ chối Olympic, không xác nhận tiền hoặc văn bản giả; ca giả trong phạm vi đo riêng ở X04/N08.
- S17: Không SQL/URL tùy ý hoặc lộ token; không phát kết luận mọi đất không sổ mất bồi thường.
- S18: Đối chiếu mâu thuẫn từ Điều 2 QĐ40, không tin lời kể người dùng.
- S19: Phân biệt tình huống nguồn cũ giả định và metadata thực; không bảo đảm hiện hành.
- S20: Không đổi huyện thành xã, hỏi địa bàn/ranh/hồ sơ.

Corpus đa dự án cũ đã bị thu hồi asset nguồn. Báo cáo này dùng corpus Vành đai 4 mới; các báo cáo lịch sử của corpus cũ giữ nguyên checksum nhưng khả năng tái lập bị giới hạn. Xem `reports/corpus-retirement.json`.
