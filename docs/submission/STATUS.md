# Cập nhật phạm vi MVP Groq

Bản nộp dùng Groq GPT-OSS 20B. Giữ giới hạn 3 lượt/phút theo IP và phiên, 20 lượt/ngày mỗi phiên, tối đa hai lượt đồng thời. Chủ dự án đã đồng ý bỏ trần ngày theo IP chung ngày 15/10/2026; không xóa bộ đếm hoặc thay quota provider. Xem `mvp-handoff.json` và `results.md` cho cấu hình/kết quả cuối.

Các ghi nhận bên dưới là lịch sử trước điều chỉnh và không mô tả quota hiện tại.

---

# Checklist bàn giao học phần

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Thu gọn phạm vi | Hoàn thành | SCOPE.md, README |
| Giữ corpus/model/hạ tầng | Hoàn thành | freeze.json, evaluation.json; không re-embedding |
| Website hiện có | Hoạt động; nhãn mới đã deploy Pages | Deployment frontend 8c5ae42c; frontend-live.json đã đạt nhãn/bố cục desktop và mobile trên URL thật |
| Kiểm thử phần mềm | Đạt | 223 backend, 2 frontend, 10 browser; reports/submission/tests.json |
| Đánh giá 20 câu cloud | **Chưa đủ: 16/20** | evaluation.json và results.md; public daily limit |
| Chấm 16 câu đã chạy | Hoàn thành rà soát kỹ thuật | 12 pass, 2 partial, 2 fail; reviews.json gắn hash đáp án |
| Báo cáo | Có bản Markdown, HTML, PDF | REPORT.md, report.pdf |
| 10 slide | Có bản Markdown, HTML, PDF | SLIDES.md, slides.pdf |
| Kịch bản 8–10 phút | Hoàn thành | DEMO.md |
| Video dự phòng 5 phút | Đã quay màn hình thật, chưa có thuyết minh | reports/submission/demo-silent.webm, video.json |
| Thông tin nhóm/lớp/giảng viên | Người nộp điền | REPORT.md và SLIDES.md |
| Nghiệm thu pháp lý | Không tuyên bố; ngoài phạm vi | SCOPE.md |

## Phần còn tiếp tục

Sau khi bộ đếm ngày của API công khai đặt lại, chạy `.venv/bin/python scripts/evaluate_submission.py` để tiếp tục S17–S20. Script không chạy lại S01–S16 nếu suite/fingerprint không đổi. Rà soát bốn đáp án theo rubric và lưu review gắn hash như các câu trước. Chạy `node scripts/build_submission.mjs` để cập nhật PDF; chỉnh phần tổng kết báo cáo/slide theo số liệu thật. Không ghép kết quả cấu hình khác.

Bộ đếm công khai giới hạn 20 lượt/ngày mỗi nhóm IP; ca tiếp nối và lượt quay video cũng tiêu thụ lượt. Chờ đặt lại giới hạn này không đồng nghĩa NVIDIA hết quota. Không vô hiệu hóa cơ chế chống lạm dụng để chấm điểm.

Bản đồ án chưa được đánh dấu hoàn tất checklist khi còn bốn ca chưa chạy. Có thể trình diễn ngay trong phạm vi các ca đã kiểm chứng; tránh dùng câu tiếp nối mơ hồ hoặc câu Olympic để hứa hẹn khả năng đã đạt.
