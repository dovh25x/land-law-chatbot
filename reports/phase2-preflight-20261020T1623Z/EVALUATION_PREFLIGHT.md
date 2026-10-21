# Evaluation preflight — chưa chạy model

Không có Groq, LLM judge hoặc full model evaluation trong Phase2. Unit tests dùng FakeProvider/FakeJudge; audit parser không sinh embedding. Không có điểm benchmark mới trong báo cáo này.

## Identity và bộ khóa

- Runtime SQLite: `2dab4dde69323ce35e9732748df40ce15c371d6380d694137a65faf05eccc179`.
- Runtime PostgreSQL dự kiến từ cùng code/settings: `c5008efb7d44adb552371982cdc122b08f7bc3d5656cb8d2ba8362f56f743bda`.
- Corpus: `corpus-a26bc99e541fbbe2`; 60 tài liệu, 7.392 chunks, E5 ONNX Q8 384 chiều giữ nguyên.
- 20 smoke +4 supplemental +8 natural giữ nguyên bytes/freeze, không thiếu gold chunk. Hash ở `corpus-audit.json` và `evaluation-case-taxonomy.json`.
- Sidecar taxonomy **đề xuất để review**, không sửa gold:19 answerable,5 cần thông tin người dùng,4 ngoài phạm vi,2 thiếu nguồn,2 safety/meta. Suite legacy chưa có trường answerability; không coi null là unanswerable. Có20 ca có gold dùng cho retrieval, gồm S02 kiểm tra hiệu lực tương lai.
- Historical/future applicability: S02–S08, X01–X03, N01–N05; conflict trực tiếp S18; partial repeal S03; replacement Hà Nội S01/S13/S14/N06; S14 dùng history đã freeze. Các ca Hà Nội/Vành đai4 và dự án ngoài phạm vi đều được giữ.
- S06 giữ FAIL ở attempt SQLite cuối, không tuning hay gọi lại. Không nhập kết quả SQLite vào cohort PostgreSQL như thể đã đo. Corpus/settings/receipts/backend thay đổi thì báo cáo cũ chỉ là evidence lịch sử.

## Metric, công thức và hiện trạng

| Metric | Công thức/ground truth | Công cụ và trạng thái | Hạn chế phải công bố |
|---|---|---|---|
| Retrieval Recall@5 | Mỗi ca có gold: `len(set(top5)&set(gold))/len(set(gold))`; macro trên20 ca, tách11 smoke/3 supplemental/6 natural | Evaluator hiện xuất top8 và Recall@8. Chuẩn bị phép tính @5 từ hits có thứ tự; **chưa đo @5 mới** | Query gốc/E5 local/backend riêng; tách S14 có history; không nhầm hit-rate với recall, không coi parent là gold leaf |
| Faithfulness | Claim được context thực tế hỗ trợ / tổng claim factual đã tách trong mẫu | Script custom theo claim support; SAMPLE cố định S04/S05/S06/S07/S08/S14/X01/X03, không phải package Ragas. Review thủ công hoặc judge sau approval | Judge cùng model không độc lập; zero claims=N/A, không phải1; missing/error giữ nguyên; verdict runtime không phải điểm |
| Citation Accuracy | Cặp claim–citation chứng minh đúng nội dung được quy cho citation đó / số cặp được công bố | Hiện có **citation integrity**, chưa có automated semantic accuracy. Chuẩn bị review gắn answer checksum/claim index/citation ID | Không citation=N/A. ID/excerpt/URL/checksum khớp chưa chứng minh entailment. Claim cần nhiều nguồn phải ghi rõ vai trò từng nguồn |
| Answer Correctness | `pass/answerable_expected` theo rubric khóa, giữ pass/partial/fail riêng và coverage review | Review nguồn/rubric gắn `answer_sha256` đã có; chưa có điểm mới. Taxonomy cần review trước chấm | Task success toàn32 không phải độ chính xác pháp luật. False abstention trên answerable là fail. Partial không tự đổi pass; missing/error ghi riêng |
| Latency | p50/p95 `elapsed_ms` theo cohort, luôn công bố n và cách percentile | Telemetry/thống kê usage đã có; **chưa có latency model mới** | Tách answered/refusal/error, CLI/public/cold start; n nhỏ chỉ mô tả. GET metadata không phải p95 chat |

Faithfulness tham khảo [định nghĩa Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/). Không cài thêm framework hoặc đổi provider/embedding để lấy tên metric.

Theo dõi riêng sau khi taxonomy được review:

- Answered rate = answered/32, kèm số đã thực thi/lỗi/chưa chạy.
- Correct refusal rate = số ca được review từ chối/hỏi lại đúng / số ca rubric yêu cầu hành vi đó; safety/meta chấm riêng.
- False refusal rate = answerable có nguồn đủ nhưng bị từ chối /19. S06 không bị bỏ để tăng điểm; provider error/missing là cột riêng.
- Cohort chưa đủ thì công bố coverage và missing/null; không lấy tỷ lệ riêng các ca dễ đã xong làm điểm complete. Không đánh đồng answered với đúng.

## Isolation và evidence

1. Dùng helper candidate với SQLite tạm hoặc PostgreSQL **mới, riêng và được phê duyệt**. Không dùng thẳng `land-law benchmark` với `.env` operator vì có thể trỏ serving/owner DB.
2. Helper generation xóa cả URL cho SQLite. `--postgres` tạo DB riêng và giữ receipt, nhưng vẫn thay đổi cloud nên chưa chạy ở Phase2. Không migrate/restore vào serving.
3. Faithfulness trước sửa dùng `Settings().for_operator()` nên có thể ghi usage/cooldown vào serving DB. Patch dùng SQLite tạm, không đổi prompt/SAMPLE/công thức, ghi identity judge riêng và giữ cooldown qua file. Bốn regression gồm owner/non-owner và cooldown1giờ; đang cooldown thì0 provider calls.
4. Manifest cần Git SHA/dirty status/patch hash, runtime fingerprint, corpus/backup SHA, receipt bundle SHA, suite SHA, backend, package lock, presentation và scorer SHA. Fingerprint đơn lẻ không bind mọi receipt trong DB.
5. Giữ attempt/checkpoint, contexts thực tế, structured output, citations, verifier verdict, usage/latency. Không key, provider error body hoặc hidden reasoning. Review gắn đúng answer checksum.
6. Không re-score để chọn điểm tốt; archive judge error/checkpoint trước resume. Script sampled judge hiện lưu checkpoint theo ca; chưa chứng nhận lưu mọi HTTP judge attempt. Chưa chạy judge ở bước này.

## Request/token budget đề xuất — không phải kết quả đo

| Công việc | API requests | Phân bổ token đề xuất |
|---|---:|---:|
| Phase2 hiện tại | **0 Groq/0 judge** | **0** |
| Pilot tương lai tối đa6 ca nội dung, không S06 | Trần36, gồm retry/repair | 60.000, nằm trong budget tổng |
| Tối đa31 ca không S06 của bộ khóa | Trần186 generation; ca guard có thể dùng0 | 150.000 generation cho đợt đầu, không cam kết đủ để hoàn thành |
| Sample judge sau approval, tối đa8ca/2requests | Trần16, thấp hơn khi missing/N/A; không chạy lại chat S06 | 40.000, có thể thay bằng review thủ công |

150.000+40.000 là mức phân bổ190.000 cho một đợt có kiểm soát, **không phải dự báo usage hay quota còn lại**. Pilot nằm trong budget tổng, không là vòng chạy thêm để chọn điểm. Phải xác nhận quota thực và phần dành cho demo trước khi bắt đầu; dừng trước ca tiếp nếu thiếu dự phòng.

Trần tổng generation31ca +judge8ca:202 requests. Nếu S06 không có trong cohort backend mới, giữ mẫu số32 và missing của cohort đó, kèm FAIL SQLite, không tuyên bố32ca PostgreSQL đã đo. Chỉ tái sử dụng attempt S06 có sẵn khi **cùng toàn bộ identity/backend**, không gọi lại; failure không được đổi pass.

Concurrency1; tối đa6 LLM requests/12tools/2retrieval rounds/1repair/90giây mỗi lượt chat. Đọc Retry-After/token-reset, giữ cooldown, không xoay key. Chờ quá cửa sổ thì checkpoint/dừng, không tự chạy nền. Chốt case IDs và quota với người dùng trước mọi lời gọi thật.

## Phần chưa đủ để chứng nhận evaluation cuối

Chưa có Recall@5/semantic Citation Accuracy chuẩn hóa cho cohort mới; taxonomy cần review; chưa chạy model/judge hoặc PostgreSQL isolation mới; chưa có public chat latency. S06 vẫn fail và là hạn chế đã chốt. Preflight không thay thực nghiệm.
