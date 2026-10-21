# C02 independent allocation — QA review

**Kết luận case: INCOMPLETE. Kết luận tính trung thực evidence: PASS_REVIEW.** Đây là hai kết luận khác nhau; không đánh dấu model answer PASS.

Attempt duy nhất được chạy ngày 21/10/2026 lúc 16:47 giờ Việt Nam trên SQLite riêng, runtime fingerprint `1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d`, model `openai/gpt-oss-120b`. Một request HTTP thực tế; tổng attempt 6.951 ms, wire request 5.252 ms. Không có lần chạy lại hoặc judge request ngoài pipeline được ghi nhận.

## Context và safety

QA đối chiếu nội dung thực tế trong `wire/01/request.json`, không chỉ preflight/intermediate capture:

- Câu hỏi khớp case C02 khóa; history trống, không gửi expected answer/gold/fixture claims/corpus backup.
- Đủ 3/3 đoạn bắt buộc: Luật Đất đai Điều 108; QĐ40/2026 Điều 17; NĐ49/2026 Điều 11.
- Text actual wire khớp từng source trong synthesis snapshot; snapshot sources thuộc admitted source IDs.
- Cả năm synthesis passages đều fresh theo checksum và ngày hỏi 21/10 trên receipt gate trong SQLite QA riêng.
- Không phát hiện configured secrets hoặc credential patterns trong artifacts pilot. Không lưu Authorization header, hidden reasoning hoặc failed_generation.
- Không có published claim/citation. Không có semantic verifier verdict vì chưa nhận được Draft hợp lệ.

## Nguyên nhân xác nhận được

Request đầu trả **HTTP400 `json_validate_failed`**, không phải HTTP429. Error body của provider nêu rõ output bị truncate do giới hạn `max_completion_tokens=2048`, thiếu các properties bắt buộc `missing_facts`, `next_steps`, `out_of_scope`. Vì đây là provider validation error trước khi có application Draft, không quy cho app JSON parser.

Không lưu truncated `failed_generation`, nên không có căn cứ đánh giá nội dung pháp lý của draft lỗi hoặc suy ra model đã/không phân biệt đúng điều kiện hỗ trợ. Không sửa schema, prompt, model hoặc giới hạn token để thử lại.

Provider không trả usage. Ledger giữ **19.788 tokens upper bound**, không ghi nhận đó là actual consumption. `confirmed_usage=0` chỉ nghĩa không có usage được xác nhận. Allocation 25.000 còn 5.212; request kế tiếp bị `test_token_cap` chặn trước network. Riêng framing allowance 4.096 + max output 2.048 đã là 6.144, vượt phần còn lại dù chưa cộng request body. Vì vậy budget stop có cơ sở bảo thủ, không có bằng chứng double-request ngoài dự kiến.

Headers lưu token limit 8.000, remaining 4.615 và reset 25,387 giây; request limit 1.000, remaining 999. Không tự gọi những số này là RPM/RPD/TPD chính xác khi chưa có metadata định nghĩa trong run; đây không phải tổng số token thực tế của attempt. Không có provider quota exhaustion HTTP429 trong attempt này. Preflight đã nói rõ live quota headroom không được kiểm chứng riêng.

## Điều được và chưa được đo

| Hạng mục | Kết quả |
|---|---|
| One attempt / one actual HTTP / ≤90 giây | PASS |
| Context completeness và snapshot membership | PASS |
| Exact freshness cho case date | PASS |
| Ledger bảo thủ, không refund usage chưa biết | PASS |
| Model legal answer | INCOMPLETE |
| Answer Correctness | NOT MEASURED |
| Semantic Citation Accuracy / Faithfulness | NOT MEASURED |
| False Abstention Rate | Không chấm case lỗi vận hành này như semantic refusal |

Giữ nguyên S06 FAIL và C01 INCOMPLETE lịch sử; C02/C03 vẫn NOT RUN trong **Phase 3A**. C02 mới là evidence độc lập với allocation 25.000, không thay trạng thái artifact Phase 3A.

QA không gọi API/model, không sửa pilot artifacts, runtime hoặc historical evidence. Chi tiết checks và SHA256 từng artifact ở [c02-pilot-review.json](c02-pilot-review.json).
