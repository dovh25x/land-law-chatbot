# Pilot đề xuất — chưa được phép gọi model

IDs đã chọn trước measurement: **S01, S04, X01, N02, N07, N08**. Xem `pilot-plan.json`. Giữ nguyên gold, rubric và toàn bộ 32 ca; không đổi IDs sau khi thấy điểm. Không gọi lại S06. FAIL cũ được giữ, cohort mới ghi chưa chạy nếu khác identity.

| ID | Vai trò | Nguồn/ngày hỏi | Ngân sách generation |
|---|---|---|---|
| S01 | Hà Nội: thay thế văn bản | QĐ 40 Điều 2; 12/10/2026 | 0, dùng no-generation guard |
| S04 | Chuyển tiếp khi đã có cả quyết định thu hồi và phương án phê duyệt | NĐ 88 Điều 31; 02/08/2024 | ≤6 requests gồm retry/repair |
| X01 | Ngôn ngữ người dân: chi phí di chuyển tài sản | Luật 31 Điều 104; 02/08/2024 | ≤6 |
| N02 | Hỗ trợ ổn định đời sống: phạm vi và điều kiện | NĐ 88 Điều 19; 02/08/2024 | ≤6 |
| N07 | Thiếu hồ sơ riêng, không bảo đảm quyền lợi | Không phát claim bảo đảm suất tái định cư | 0, no-generation guard |
| N08 | Viện dẫn văn bản chưa có nguồn | Không xác nhận nội dung văn bản giả định | 0, no-generation guard |

Trần generation là 18 requests. Judge tối đa 4 requests cho S04/X01, hai ID giao với SAMPLE faithfulness đang có. **Tổng pilot ≤22 requests**, phân bổ **32.000 generation +8.000 judge =40.000 tokens**. Đây là ngân sách đề xuất, không phải usage đo hoặc cam kết đủ quota. Phase 2B có 0 request Groq.

Pilot nằm trong full allocation đề xuất 150.000 generation +40.000 judge =190.000 tokens; không cộng thêm 40.000 vào tổng này. Trần full đề xuất 202 requests (31 ca không chạy lại S06 ×6 +8 judge ×2) là mức bảo thủ, không phải chỉ tiêu phải tiêu hết. Public smoke có gọi model cần approval riêng, dùng ngân sách còn lại và không thay attempt pilot bằng kết quả đẹp hơn.

Chưa xác nhận quota thực tế của Groq. Chạy concurrency 1, tuân thủ Retry-After/token reset/cooldown; mỗi chat vẫn giữ 6 requests, 12 tools, 2 retrieval rounds, 1 repair và 90 giây. Token allocation không phải trần tuyệt đối khi request lỗi không trả usage. Kiểm dung lượng trước từng ca, giữ dự phòng demo; hết cửa sổ/quota thì checkpoint và dừng.

## Cách chấm

| Metric | Công thức và bằng chứng | Hiện trạng |
|---|---|---|
| Recall@5 | Macro `len(top5∩gold)/len(gold)` trên S01/S04/X01/N02; lưu top8 có thứ tự, gold và backend | Có diagnostic SQLite 4 ca; `pilot-retrieval-final.json`. Chưa phải full-suite/PG score |
| Faithfulness | Tách claim factual, xét hỗ trợ từ context thực tế; zero-claim=N/A | Script custom, không phải package Ragas. S04/X01 có thể dùng SAMPLE cố định sau approval; các claim khác review thủ công, ghi phương pháp riêng. Chưa có điểm model mới |
| Citation Accuracy | Review cặp atomic fact–citation: đúng chủ thể, điều kiện, ngoại lệ, phiên bản và nội dung quy cho nguồn | Mới kiểm integrity; semantic accuracy chưa được đo |
| Answer Correctness | Rubric khóa; bốn ca answerable S01/S04/X01/N02; giữ pass/partial/fail và answer checksum | Từ chối ca đủ nguồn là fail, không bỏ khỏi mẫu số |
| Latency | Lưu elapsed mỗi attempt; tách answered/refusal/error, SQLite/PG, CLI/public, cold/warm | Chưa đo model/public chat. N nhỏ chỉ mô tả, không dùng p95 pilot như SLA |
| Answerable Coverage | Số answered/4; công bố thêm correctly_answered/4 và review coverage | Không đổi nhãn answerable để làm tỷ lệ đẹp |
| False Abstention Rate | Số clarification/insufficient trên bốn ca answerable đủ nguồn /4 | Error/not-run ghi riêng. N07/N08 không thuộc mẫu số này; đánh giá hành vi hỏi lại/từ chối riêng |

Taxonomy là sidecar đề xuất cần review, không sửa gold. S02 của full suite có legal fact bắt buộc và cần thêm dữ kiện; không tự coi mọi clarification là đúng nếu thiếu legal fact theo rubric. Faithfulness và citation integrity không thay thẩm định pháp lý.

## Thực thi sau approval

1. Chốt policy, receipts, model và runtime trước lời gọi trả phí. Nếu dùng cohort đại diện cloud, kiểm PostgreSQL riêng trước; không tự trộn kết quả SQLite vào PostgreSQL.
2. Khóa corpus, suite, receipt bytes, runtime/presentation/scorer hashes và backend vào output mới. Helper nhận `--source-receipt` và `--source-gate`; scoped backup thiếu receipt phải dừng trước model.
3. Chạy nhóm 0 LLM bằng `--no-generation`; chạy đúng ba ca nội dung một lần sau approval. Pilot là phần đầu full run; resume cùng output/identity cho phần còn lại, không chạy lại pilot. Giữ mọi attempt và cooldown.
4. Review đáp án/citations theo rubric. Judge chỉ nhận câu hỏi giả lập và context pháp luật công khai; giữ SAMPLE và missing cases, không gọi lại chat S06.
5. Nếu policy/receipt đổi sau pilot, giữ cohort cũ và xin ngân sách cho cohort mới; không chuyển nhãn hoặc chọn điểm đẹp.
