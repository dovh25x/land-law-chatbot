# Kiểm tra tài liệu xuất

Phạm vi: chất lượng file học thuật; không phải legal review, model evaluation hoặc nghiệm thu cloud.

- Báo cáo A4 tiếng Việt có bìa trống, mục lục có liên kết, 12 chương, references nguồn nghiên cứu và URL pháp luật chính thức được dẫn từ biên bản đã lưu.
- PDF được render offline bằng Chromium, chặn HTTP/HTTPS; font chữ được nhúng. Script đọc lại text, kiểm trang trắng, disclosures, page sizes và font descriptors.
- Slide PDF 12 trang, tỉ lệ 16:9. Script kiểm bounding boxes/overflow trên HTML của cả 12 slide; preview bìa và slide metrics đã xem trực quan.
- PPTX 12 slide editable, 12 speaker notes, có ảnh kiến trúc raster từ đúng SVG/HTML diagram-design đã có. Kiểm ZIP/XML và ước lượng text layout bằng DejaVu Sans không phát hiện overflow.
- Một số trang PDF báo cáo được render lại bằng PDFium để xem bìa, đoạn văn, bảng và số trang. Kiểm thị giác không phải đọc duyệt mọi câu hoặc chứng minh đầy đủ rubric học phần chưa được cung cấp.
- PDF slide được render từ HTML cùng `slides.json`, không chuyển trực tiếp bằng PowerPoint. Native PowerPoint/LibreOffice rendering **NOT TESTED**; cần rehearsal hoặc dùng PDF để tránh thiếu font trên máy bảo vệ.

Kết quả máy đọc mới nhất nằm ở [asset-validation.json](asset-validation.json). Không cộng kiểm file thành test phần mềm và không dùng PASS export để đánh dấu deployment/model PASS. Các preview PNG là artifacts có thể giữ ngoài Git; không thay nguồn văn bản hoặc ảnh nội dung legal answer.

Kết quả quan trọng được công bố: SQLite Recall@5 macro 97,37% trên 19 câu, micro 20/21 = 95,24%; không phải answer accuracy. S06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN trong Phase 3A. C02 allocation mới INCOMPLETE, 1 HTTP 400, không có đáp án phát hành. Tình trạng release cập nhật riêng trong delivery status; bản bàn giao source-only đã có evidence local/CI/public browser riêng; model generation vẫn tắt.

Provenance xuất cuối được kiểm bằng `build-source-identity.json` và `export-identity.json`: đổi status, prose hoặc renderer sau build phải rebuild/export trước khi package. PASS của validator gắn các hash đó; script ZIP không dùng PDF cũ để mang trạng thái mới. Các files sinh sau code commit được công bố như tài liệu/Release assets có checksum, không giả là đã nằm trong Docker hoặc đã được CI kiểm runtime.


Xuất cuối: báo cáo 29 trang A4; slide PDF 12 trang và PPTX 12 slide/12 speaker notes. Validator PASS: glyph bounds trong trang, không trang trắng hoặc HTML overflow; font PDF nhúng đầy đủ. Báo cáo có 87 URI annotations, không file://, /home/, localhost hoặc địa chỉ local; evidence anchors chuyển sang stable tag và binary links sang Releases download. Reachability của tag chưa kiểm trong offline export vì release owner xuất bản sau khi đóng gói. Bìa, slide metrics và một số trang bảng đã xem lại trực quan; không thay thế rehearsal/native PowerPoint.
