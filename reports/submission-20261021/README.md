# Gói nộp đồ án — Hanoi Land Law Assistant

Ngày chuẩn bị: **21/10/2026, giờ Việt Nam**. Phạm vi: tra cứu có nguồn về bồi thường, hỗ trợ và tái định cư cho Vành đai 4 tại Hà Nội. Không xác định thửa đất, tính tiền hoặc cam kết quyền lợi cá nhân. **Candidate hiện tại chỉ tra cứu đoạn nguyên văn đã review, tắt sinh đáp án AI** (`SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`). Local API PASS; 529 backend / 16 frontend / 104 Playwright fixtures và build PASS; cloud chưa được xác minh tại mốc này.

| Tệp | Mục đích |
|---|---|
| [Final_Project_Report.pdf](Final_Project_Report.pdf) | Báo cáo học thuật tiếng Việt, 12 chương, references và cập nhật release |
| [Final_Project_Report.md](Final_Project_Report.md) / [HTML](Final_Project_Report.html) | Nguồn biên soạn/xuất báo cáo |
| [Final_Project_Presentation.pptx](Final_Project_Presentation.pptx) | 12 slide có thể chỉnh sửa để bảo vệ |
| [Final_Project_Presentation.pdf](Final_Project_Presentation.pdf) | Bản trình chiếu PDF dự phòng |
| [EVALUATION.md](EVALUATION.md) | Công thức, mẫu số, cohort và những chỉ số chưa đo |
| [DEMO_GUIDE.md](DEMO_GUIDE.md) | Demo evidence thật, nhãn fixture và phương án khi API/cloud lỗi |
| [LIMITATIONS.md](LIMITATIONS.md) | Giới hạn pháp lý, thực nghiệm, privacy và deployment |
| [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) | Các bước cuối trước nộp/bảo vệ |
| [delivery-status.json](delivery-status.json) | Trạng thái mới nhất do release owner cung cấp; không thay lịch sử |
| [asset-validation.json](asset-validation.json) | Page/slide count, fonts, text và checksum kiểm xuất |
| [Evidence index Phase 4](../final-submission/2026-10-21/EVIDENCE_INDEX.md) | Liên kết bằng chứng gốc, không nhân bản cây artifacts |

Các trường sinh viên/MSSV/học phần/GVHD để trống theo yêu cầu. Không có rubric chính thức trong repository. **97,37% là macro retrieval Recall@5 trên 19 câu SQLite, không phải độ đúng đáp án pháp luật.** S06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN trong Phase 3A được giữ nguyên. Pilot C02 allocation độc lập mới đã chạy đúng một attempt: **INCOMPLETE**, 1 HTTP 400 JSON, không có đáp án phát hành; ghi riêng, không ghi đè kết quả cũ.

## Tái xuất tài liệu

Công cụ tài liệu được cài độc lập vào `/tmp`, không đổi dependencies runtime:

```bash
.venv/bin/python -m pip install --target /tmp/landlaw-submission-tools -r reports/submission-20261021/document-tools.txt
node reports/submission-20261021/export_pdf.cjs --prepare-assets-only
PYTHONPATH=/tmp/landlaw-submission-tools .venv/bin/python reports/submission-20261021/build_assets.py
node reports/submission-20261021/export_pdf.cjs
PYTHONPATH=/tmp/landlaw-submission-tools .venv/bin/python reports/submission-20261021/validate_assets.py
```

Cần Node, frontend `node_modules`/Playwright Chromium đã cài và font DejaVu Sans/Serif hỗ trợ tiếng Việt. `build_assets.py` không gọi model/network/DB; `export_pdf.cjs` chỉ mở HTML local. `prepare_sources.py` là thao tác nhập prose Phase 4 ban đầu: không chạy lại sau khi đã chỉnh sửa bản báo cáo. Chạy build sau khi sửa `delivery-status.json`/`slides.json`; HTML/PDF/PPTX sẽ có cùng nội dung cập nhật. Tool versions được ghim; PDF có metadata theo lần export nên không cam kết checksum byte giống nhau sau tái xuất.

Giữ cấu trúc thư mục repo khi review các liên kết evidence. Khi nộp PDF/PPTX riêng, gửi kèm source release/evidence index và release manifest từ release owner; các assets corpus/model lớn có checksum được giao riêng. Không đưa `.env`, SQLite riêng, API keys hay backup production vào gói nộp.

PDF slide được render từ cùng nội dung `slides.json` qua HTML; không phải phép chuyển đổi PPTX bằng Microsoft PowerPoint/LibreOffice. PPTX được kiểm cấu trúc, text, số slide/notes và có ảnh sơ đồ; render trực tiếp trong PowerPoint chưa kiểm trên môi trường này. Nếu máy trình chiếu thiếu DejaVu Sans, dùng PDF đã nhúng font hoặc cài font hợp lệ trước rehearsal.
