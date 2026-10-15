# Gói nộp đồ án

1. Đọc `SCOPE.md` để biết yêu cầu hiện hành.
2. Điền thông tin sinh viên/lớp/giảng viên trong `REPORT.md`, xuất PDF bằng công cụ soạn thảo của nhóm.
3. `SLIDES.md` chứa nội dung 10 slide; `DEMO.md` là kịch bản 8–10 phút và video 5 phút.
4. Xem `reports/submission/results.md`: chưa chấm phải ghi chưa chấm, không điền số liệu giả vào slide.
5. Chạy lại đánh giá: `.venv/bin/python scripts/evaluate_submission.py`. Dùng endpoint cloud cố định, không cần khóa API trên máy đánh giá. Checkpoint sẽ tiếp tục khi cùng suite/cấu hình. Hết giới hạn theo ngày thì chờ, không tạo phiên để né giới hạn.
6. Bảo toàn mã nguồn và kết quả lịch sử. Các gate production vẫn giữ nguyên nhưng không còn là tiêu chí học phần.

## Tái lập local

Theo mục chạy phát triển trong README gốc. Cần `.env` riêng (không nộp khóa), dữ liệu/backup có quyền truy cập và E5 model. Local trống không tự có corpus cloud. Nếu dùng backup, thực hiện restore vào database riêng theo `docs/OPERATIONS.md`; không chạy restore đè cloud để demo. Website là đường trình diễn chính, video là phương án dự phòng.

## Cấu hình và phiên bản

`reports/deployment-current.json`: deployment cloud được ghi nhận trước đây. `reports/submission/evaluation.json`: release/fingerprint thực sự kiểm tra mới. `runner_commit` chỉ là commit của công cụ chạy, không phải bằng chứng commit backend. Khi chưa deploy code mới phải nói rõ frontend/source và backend cloud có thể khác phiên bản.

## Artifact xuất sẵn

- `report.pdf`, `report.html`: báo cáo có bảng kết quả thực tế.
- `slides.pdf`, `slides.html`: 10 slide; Markdown gốc có thể chỉnh sửa.
- `reports/submission/demo-silent.webm`: video màn hình thật 5 phút, **không thuyết minh**, gồm chat Điều 104, nguồn, trace và điều hướng; không bao phủ hết kịch bản nói.
- Xuất lại sau khi đổi kết quả: `node scripts/build_submission.mjs` (cần Chromium Playwright).
- Video được quay trước khi nhãn học thuật mới triển khai; xem ngày và nhãn thực tế trong `reports/submission/video.json`. Không suy video là chứng nhận chất lượng.
