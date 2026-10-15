# Gói nộp đồ án

1. Đọc `SCOPE.md` để biết yêu cầu hiện hành.
2. Điền thông tin sinh viên/lớp/giảng viên trong `REPORT.md`, xuất PDF bằng công cụ soạn thảo của nhóm.
3. `SLIDES.md` chứa nội dung 10 slide; `DEMO.md` là kịch bản 8–10 phút và video 5 phút.
4. Xem `reports/submission/results.md`: chưa chấm phải ghi chưa chấm, không điền số liệu giả vào slide.
5. Công cụ đánh giá HTTP lịch sử: `.venv/bin/python scripts/evaluate_submission.py`. Dùng endpoint cloud cố định, không cần khóa API trên máy đánh giá. Checkpoint sẽ tiếp tục khi cùng suite/cấu hình. Hết giới hạn theo ngày thì chờ, không tạo phiên để né giới hạn.
6. Bảo toàn mã nguồn và kết quả lịch sử. Các gate production vẫn giữ nguyên nhưng không còn là tiêu chí học phần.

## Tái lập local

Theo mục chạy phát triển trong README gốc. Cần `.env` riêng (không nộp khóa), dữ liệu/backup có quyền truy cập và E5 model. Local trống không tự có corpus cloud. Nếu dùng backup, thực hiện restore vào database riêng theo `docs/OPERATIONS.md`; không chạy restore đè cloud để demo. Website là đường trình diễn chính, video là phương án dự phòng.

## Cấu hình và phiên bản

`reports/submission/mvp-handoff.json`: trạng thái bàn giao mới. `reports/deployment-current.json`: deployment cloud lịch sử. `reports/submission/evaluation.json`: release/fingerprint thực sự kiểm tra mới. `runner_commit` chỉ là commit của công cụ chạy, không phải bằng chứng commit backend. Khi chưa deploy code mới phải nói rõ frontend/source và backend cloud có thể khác phiên bản.

## Artifact xuất sẵn

- `report.pdf`, `report.html`: báo cáo có bảng kết quả thực tế.
- `slides.pdf`, `slides.html`: 10 slide; Markdown gốc có thể chỉnh sửa.
- `reports/submission/demo-silent.webm`: video màn hình thật 5 phút, **không thuyết minh**, gồm chat Điều 104, nguồn, trace và điều hướng; không bao phủ hết kịch bản nói.
- Xuất lại sau khi đổi kết quả: `node scripts/build_submission.mjs` (cần Chromium Playwright).
- Kiểm tra model/ngày quay/trạng thái trong `reports/submission/video.json`; video cũ hoặc partial không chứng nhận bản Groq. Không suy video là chứng nhận pháp lý.

## Tái lập bộ 20 ca của bản Groq

Chạy CLI trên commit backend được ghi trong receipt, với cấu hình Groq/E5 khớp bản nộp:

```bash
.venv/bin/land-law benchmark --split smoke --release-id corpus-de584c31fc95f9a2 --mode agentic --concurrency 1
.venv/bin/python scripts/export_mvp_evaluation.py --run-dir reports/runs/<run-id>
```

Công cụ chỉ xuất đánh giá, không tự chấm nội dung. `reviews.json` gắn với checksum từng câu trả lời; kết quả mới bắt buộc rà soát lại. `--public-summary reports/latest.json` chỉ chạy khi đủ ca được rà soát; báo cáo luôn giữ `acceptance_passed=false`. Bản này có 16 pass / 3 partial / 1 fail, không phải nghiệm thu bộ 80 câu.
