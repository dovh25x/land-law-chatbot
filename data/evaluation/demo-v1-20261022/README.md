# Bộ đánh giá demo v1 — 22/10/2026

Bộ nhỏ gồm 12 kịch bản được khóa trước khi gọi model:

| Nhóm | Số ca | Cách chạy |
|---|---:|---|
| Hội thoại xã giao | 4 | Không retrieval, không citation, không gọi Groq |
| Hỏi pháp luật | 5 | Đúng một request Groq cho mỗi ca, tuần tự |
| An toàn/tin cậy tất định | 3 | Kiểm tra store, hiệu lực, adverse review và citation |

`manifest.json` ghi hash của `scenarios.jsonl`. Không sửa câu hỏi, gold hoặc tiêu chí sau khi đã xem kết quả. Mọi lần chạy phải giữ nguyên attempt; ca chưa chạy ghi `NOT RUN`, không thay bằng fixture.

## Cách tính

- **Xã giao:** đúng intent, đúng trạng thái, câu trả lời có các cụm bắt buộc, `llm_calls=0`, không citation và không retrieval. Đạt 4/4 mới coi là pass nhóm.
- **Pháp luật:** `status` phải nằm trong danh sách cho phép; citation phải là các đoạn đã truy xuất; kiểm tra cụm bắt buộc/cấm. Không tính là đạt nếu bịa số tiền, điều luật, URL hoặc quyền lợi cá nhân. Mỗi câu được đọc thủ công để chấm `task_success` và `grounded`.
- **An toàn:** cả ba kiểm tra phải đạt. Không dùng model thật.
- Không dùng RAGAS, không dùng LLM judge độc lập, không tuyên bố đây là thẩm định pháp lý.

## Lệnh

Chỉ preflight, không gọi Groq:

```bash
.venv/bin/python scripts/evaluate_demo_suite.py \
  --backup reports/final-submission/2026-10-21/local-postgres-corpus-backup.json \
  --policy reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json \
  --policy-v1 reports/source-review-20261022/source-gate-20261022.json \
  --receipts reports/source-review-20261022/receipts-20261022 \
  --output reports/evaluation/demo-v1-20261022/preflight.json
```

Chạy 5 ca pháp luật thật (chỉ sau khi được duyệt ngân sách 5 request/15.000 token):

```bash
.venv/bin/python scripts/evaluate_demo_suite.py ... --live
```

Runner dừng khi hết 5 request hoặc 15.000 token đã đặt trước; các ca còn lại ghi `NOT RUN`. Không retry, không repair loop. Kết quả live phải được đọc và chấm thủ công trước khi dùng trong báo cáo.
