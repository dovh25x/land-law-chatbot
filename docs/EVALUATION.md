# Phương pháp đánh giá

## Mục tiêu và phạm vi

Đánh giá tách chất lượng tìm nguồn, mức hỗ trợ của chứng cứ, mức đáp ứng câu hỏi và độ ổn định thực thi. Các bộ câu hỏi là regression suite nhỏ, không đại diện toàn bộ pháp luật hoặc người dùng thực tế. Không công bố một điểm tổng hợp thay cho các chỉ số thành phần.

Unit/E2E dùng fixture để kiểm tra phần mềm. Generation benchmark và offline judge gọi model thật; kết quả của hai loại kiểm tra không được dùng thay cho nhau.

## Bộ dữ liệu và khóa phiên bản

| Suite | Số ca | Vai trò |
|---|---:|---|
| `smoke` | 20 | Quy định, hiệu lực, ngữ cảnh, hỏi làm rõ và từ chối |
| `supplemental` | 4 | Regression probes cho lỗi đã xác định |
| `natural` | 8 | Câu hỏi tự nhiên và các trường hợp giới hạn |

JSONL và freeze/checksum nằm trong `data/evaluation/`. Giữ nguyên bộ đã khóa; không đổi gold hoặc tiêu chí sau khi thấy đáp án để tăng điểm. Những hạn chế annotation được ghi trong báo cáo thay vì sửa ngầm.

Mỗi ca chạy một lần trên cấu hình cuối. Chỉ chạy lại khi lỗi thực thi hoặc thay đổi liên quan; giữ mọi attempt và retry count. Không lựa chọn đáp án tốt nhất từ nhiều lượt.

## Chỉ số

| Chỉ số | Định nghĩa | Giới hạn diễn giải |
|---|---|---|
| Gold Recall@8 | Mỗi ca có gold: số gold chunk trong top 8 chia tổng gold chunk; tổng hợp macro-average | Đo retrieval, không phải chất lượng đáp án |
| Sampled faithfulness | Tổng mệnh đề được context hỗ trợ chia tổng mệnh đề thực tế được judge tách trong mẫu | Phụ thuộc tách claim và chất lượng judge |
| Task success | Review `pass`/`partial`/`fail` theo tiêu chí đã khóa, tách nhóm hành vi | Hỏi lại/từ chối đúng không phải trả lời nội dung đúng |
| Citation integrity | ID, tài liệu, excerpt, locator, URL và checksum khớp corpus | Khớp nguồn không chứng minh diễn giải được nguồn hỗ trợ |
| Vận hành | Lỗi thực thi, latency, token, số lần gọi LLM/công cụ | Thống kê một lượt chạy, không phải SLA |

### Gold Recall@8

Chỉ tính ca có gold. Dùng query gốc, ghi rõ SQLite/PostgreSQL và tách nhóm phụ thuộc history. Không trộn search standalone với evidence được tìm sau agent routing, mở điều khoản hoặc mở rộng quan hệ pháp lý. Không gọi generation cho phép đo này.

### Faithfulness mẫu

Implementation tham khảo định nghĩa faithfulness của Ragas, nhưng không chạy framework hoặc thêm dependency Ragas. Tám ca cố định là S04, S05, S06, S07, S08, S14, X01 và X03.

Judge đọc đáp án cuối cùng cùng context thực tế, tự tách claim và chấm trong một request; không dùng verdict runtime verifier làm điểm. Mỗi ca tối đa một retry khi lỗi thực thi hoặc định dạng. Không có claim ghi “không áp dụng”; judge lỗi ghi chưa chấm và không thay mẫu khác.

Báo cáo công bố số ca có điểm, số claim, ca không áp dụng/lỗi, model judge và fingerprint. Judge dùng cùng model với hệ thống nên không độc lập. Giữ verdict gốc, kể cả khi reviewer nhận thấy hạn chế trong cách judge tách claim; không chấm lại chỉ để tăng điểm.

### Task success và lỗi

Review phải gắn `answer_sha256` của đúng đáp án, verdict, lý do và phương pháp rà soát. Không chuyển review từ đáp án cũ sang đáp án mới.

Tách các nhóm trả lời nội dung, hỏi làm rõ, thiếu chứng cứ/ngoài phạm vi và lỗi thực thi. Abstention giúp chặn diễn giải sai nhưng vẫn có thể fail nếu nguồn đủ mà hệ thống không trả lời được tác vụ. Ca quota hoặc lỗi không bị loại khỏi mẫu số của suite.

`status=reviewed` chỉ xác nhận suite đã chạy và được rà soát đầy đủ, bao gồm các ca fail. `execution_successful` tách riêng lỗi thực thi; hai trường này không xác nhận chất lượng pháp lý.

## Chạy đánh giá

Cấu hình database đích trước khi chạy. CLI operator có thể ưu tiên `ADMIN_DATABASE_URL`; dùng database đánh giá riêng và không seed fixture history vào database.

```bash
.venv/bin/land-law benchmark --split smoke --mode agentic --concurrency 1
.venv/bin/land-law benchmark --split supplemental --mode agentic --concurrency 1
.venv/bin/land-law benchmark --split natural --mode agentic --concurrency 1
.venv/bin/land-law retrieval-benchmark --split smoke
```

CLI không tiêu quota ứng dụng public. Budget và deadline workflow giữ như API; quota thực cùng `Retry-After` của Groq vẫn áp dụng. Evaluator có thể dừng để chờ cửa sổ provider phù hợp thay vì retry liên tục.

Export từng suite riêng, với snapshot đúng corpus:

```bash
.venv/bin/python scripts/export_mvp_evaluation.py   --run-dir <run-directory>   --release <corpus-snapshot.json>   --suite data/evaluation/smoke.jsonl   --output <versioned-report-directory>
```

Tạo `reviews.json` trong thư mục report, đối chiếu nguồn cho từng đáp án rồi export lại. Dùng `--suite` tương ứng cho supplemental/natural. Không ghép corpus, model hoặc fingerprint khác nhau.

```bash
.venv/bin/python scripts/evaluate_faithfulness.py   --run-dir <smoke-run-directory>   --run-dir <supplemental-run-directory>   --output <versioned-report-directory>/faithfulness.json
```

Export lịch sử khác source hiện tại chỉ dùng `--allow-historical` và phải giữ nguyên fingerprint đã ghi nhận. Cờ này không biến báo cáo lịch sử thành kết quả của source mới.

## Artifact và công bố

| Artifact | Nội dung |
|---|---|
| `reports/runs/<run>/` | Metadata, checkpoint, attempt và output phục vụ chẩn đoán |
| `evaluation.json`, `results.md` | Kết quả từng ca và thống kê theo nhóm |
| `reviews.json` | Review gắn checksum đáp án |
| `attempts.json` | Các attempt được giữ lại |
| `faithfulness.json` | Verdict claim, coverage mẫu và cấu hình judge |
| `reports/latest.json` | Summary được API công bố |

Chỉ dùng `--public-summary reports/latest.json` sau khi mọi ca suite chính đã chạy và review. Không sửa fingerprint để khớp deployment; frontend phải giữ cảnh báo khi khác corpus hoặc cấu hình. Trace, latency và LLM calls của CLI không thay cho xác minh HTTPS thực tế.

Nếu artifact cũ không có telemetry bước sinh Draft, ghi `answer_origin=unknown`; không suy ra có generation chỉ từ số lần gọi planner/verifier. Không có citation thì integrity là “không áp dụng”.

Báo cáo số liệu chỉ ở `reports/`; tài liệu này định nghĩa phương pháp. Xem [báo cáo có phiên bản](../reports/evaluation/ring4-c4f0c661/README.md) và [trạng thái triển khai](../reports/deployment-ring4.json). Các báo cáo corpus đã bị thu hồi asset giữ nguyên checksum và công khai hạn chế tái lập.

Rubric và readiness nội dung được giữ để đo, rà soát và công bố giới hạn; deploy mặc định không yêu cầu chúng đạt. Người vận hành có thể bật chế độ yêu cầu quality qua runbook. Việc bỏ điều kiện chặn deploy không đổi nhãn kết quả lịch sử hoặc thay kiểm chứng claim/citation trong runtime.

### Dashboard và lịch sử công khai

Chạy `.venv/bin/python scripts/build_public_evaluations.py` để tạo `reports/public-evaluations.json` từ các evaluation/retrieval/faithfulness artifact đã commit. Lệnh chỉ tổng hợp metadata theo allowlist, kiểm kê checksum, không gọi model, truy cập database hoặc sửa báo cáo gốc. Các lần dở dang, fail, limited, chưa rà soát và ca chưa thực hiện đều được công bố. Không chọn kết quả tốt nhất hoặc gộp các cấu hình khác nhau. Bản chiếu public có thể cập nhật khi bổ sung artifact; artifact đầu vào giữ nguyên.

Mặc định của dashboard là bộ đầy đủ gần nhất trên corpus đang phục vụ, không phải điểm cao nhất. Lần kiểm tra riêng mới hơn vẫn nằm trong lịch sử và selector. Source checksum và link GitHub ghim commit cho phép đối chiếu dữ liệu. Đính chính nhận xét là chú thích riêng, không sửa verdict hoặc artifact lịch sử. Các chỉ số retrieval và faithfulness giữ phạm vi, backend và fingerprint gốc, không tự chứng nhận deployment.
