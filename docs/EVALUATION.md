# Đánh giá tối thiểu

Bộ `smoke` 20 câu và `supplemental` 4 câu giữ nguyên checksum; `natural` thêm 8 câu đã khóa trước chỉnh prompt. Đây là regression probes nhỏ, không phải benchmark pháp lý đại diện. Lưu mọi attempt; chỉ chạy lại khi lỗi hoặc thay đổi liên quan. Không chọn đáp án đẹp.

| Metric | Định nghĩa |
|---|---|
| Gold Recall@8 | Với mỗi ca có gold, số gold chunk có trong top 8 / tổng gold chunk; tổng hợp macro |
| Sampled faithfulness | Mệnh đề thực tế được context hỗ trợ / tổng mệnh đề được judge tách từ đáp án cuối |
| Task success theo nhóm | Review pass/partial/fail theo tiêu chí khóa; tách trả lời, hỏi lại, thiếu chứng cứ/ngoài phạm vi và lỗi |
| Citation integrity / vận hành | Citation khớp corpus; latency, token, LLM/tool calls và lỗi; không có citation ghi không áp dụng |

Faithfulness tham khảo [định nghĩa Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/), nhưng là implementation đánh giá mẫu riêng, không chạy framework Ragas. Tám ca cố định: S04, S05, S06, S07, S08, S14, X01, X03. Offline judge tự tách claim trong một request từ đáp án cuối và context thực tế; không lấy verdict runtime verifier làm điểm. Tối đa một retry khi lỗi. Không có claim ghi không áp dụng; judge lỗi ghi chưa chấm, không thay ca.

```bash
land-law benchmark --split smoke --mode agentic --concurrency 1
land-law benchmark --split supplemental --mode agentic --concurrency 1
land-law benchmark --split natural --mode agentic --concurrency 1
land-law retrieval-benchmark --split smoke
python scripts/export_mvp_evaluation.py --run-dir <run> --output <report-dir>
python scripts/evaluate_faithfulness.py --run-dir <smoke-run> --run-dir <supplemental-run> --output <report-dir>/faithfulness.json
```

CLI là operator, không tiêu quota public. Deadline/budget workflow giống API. Groq quota và Retry-After vẫn áp dụng. Retrieval benchmark không gọi generation; dùng query gốc, nêu SQLite/PostgreSQL và tách nhóm phụ thuộc history; không trộn retrieval standalone với evidence sau agent routing.

Review gắn `answer_sha256`, verdict và lý do đối chiếu nguồn. Không chuyển review cũ sang đáp án mới. Công bố fingerprint, corpus/model/judge, coverage mẫu và giới hạn cùng model tự chấm. Citation khớp không đồng nghĩa entailment; faithfulness không thay thế đúng điều kiện pháp lý hoặc đáp ứng câu hỏi. Không tạo điểm tổng hợp.

Báo cáo cũ giữ nguyên. Khi asset corpus cũ bị thu hồi sẽ ghi nhận hạn chế tái lập trong báo cáo thu hồi riêng, không sửa checksum lịch sử. `reports/latest.json` chỉ cập nhật khi suite chính đã chạy/review đầy đủ; frontend phải cảnh báo nếu không khớp cấu hình hiện tại.
