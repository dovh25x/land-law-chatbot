# Checklist nộp đồ án

Deadline được chủ dự án cung cấp: **23/10/2026**; chưa có giờ nộp/mẫu biểu/rubric chính thức. Không tự suy thêm thời hạn trong ngày hoặc tiêu chí điểm. Các ô bìa để trống theo yêu cầu hiện tại.

| Việc | Trạng thái khi chốt Phase 4 | Người thực hiện/bằng chứng |
|---|---|---|
| Báo cáo tiếng Việt 12 chương, đúng hệ thống thực | Bản thảo có | [Final report](FINAL_PROJECT_REPORT.md), cần sinh viên đọc/đối chiếu |
| Bìa: học phần/mã/tên/MSSV/GVHD | Để trống theo yêu cầu | Chỉ điền sau khi có thông tin, không tự tạo |
| Đối chiếu syllabus/rubric/mẫu trường | NOT TESTED | Chưa nhận tài liệu, không chứng nhận đã đáp ứng |
| Mục lục, đánh số hình/bảng, bibliography theo mẫu | Chưa xuất bản | Cần xử lý khi chuyển Word/LaTeX/PDF; Markdown chưa thay PDF |
| Bộ slide 10–12 trang | Dàn ý 12 slide có | [Outline](SLIDE_OUTLINE.md), chưa có PPTX/PDF thiết kế |
| Demo có nhãn evidence/fixture và fallback | Kịch bản có | [Demo](DEMO_SCRIPT.md), chưa rehearsal với hội đồng |
| Evaluation summary và metrics chưa đo | Có | Không đổi Recall thành answer accuracy; giữ cohort/exclusions |
| Known limitations/threats to validity | Có | [Giới hạn](KNOWN_LIMITATIONS.md), cần giữ trong bản nộp |
| Evidence index và manifest/hash | Có | [Index](EVIDENCE_INDEX.md), [freeze](freeze-manifest.json); xác minh bằng script trước đóng gói |
| Các attempt lỗi được giữ nguyên | Kiểm bởi validation | S06 FAIL, C01 INCOMPLETE, C02/C03 NOT RUN; không chỉ nộp ảnh đẹp |
| Source code bao gồm untracked runtime/tests | Chưa commit | Review [allowlist](CODE_FREEZE.md); không bỏ request_budget/synthesis_context vì chưa tracked |
| Corpus/model asset và quyền phân phối | Cần giao riêng | Staging/model bị ignore; ghi checksum/provenance/license và cách lấy, không copy bừa cả data |
| Tệp corpus 39 MB trong final folder | Không đưa vào bản PDF/index phân phối mặc định | Chỉ artifact backup PG local nếu tạo; giữ trên máy, kênh giao riêng được kiểm, không xóa |
| Không `.env`, API keys, cookies, session/ingress tokens | Phải kiểm cuối | Scanner là một lớp; review cả archive/export thủ công |
| URL cloud đúng candidate và public E2E | NOT TESTED | Có checklist/runbook, không tự ghi cloud đã hoàn thành |
| File PDF đọc được, link nội bộ/hình không hỏng | NOT TESTED PDF | Phase 4 chỉ kiểm Markdown và file references, cần kiểm sau export |
| Source/evidence archive mở được trên máy khác | NOT TESTED | Không tuyên bố clone đủ corpus/model; cần bản giao asset có hash |
| Nộp đúng hệ thống/lớp và nhận biên nhận | Chưa thực hiện | Sinh viên thực hiện, agent không tự gửi bài |

## Tối thiểu trước khi nộp

1. Đọc và duyệt nội dung, điền thông tin bìa khi sẵn sàng, kiểm yêu cầu chính thức nếu có. Giữ các dòng NOT MEASURED/NOT RUN và giới hạn cloud/model.
2. Chuyển bản thảo sang định dạng được yêu cầu; làm slide từ outline và rehearsal demo minh bạch. Không dùng transcript giả để bù thiếu inference.
3. Chốt gói source/evidence có checksum và asset manifest. Giữ đường dẫn tương đối bằng cách giữ cấu trúc repository; bản PDF dùng số mục/URL phù hợp, không kỳ vọng link Markdown local còn hoạt động ngoài repo.
4. Chạy kiểm tra link/secret/hash lần cuối trên gói thực giao, xem PDF bằng trình đọc khác, kiểm font tiếng Việt, hình sơ đồ nguồn HTML/SVG và bibliography.
5. Nếu cloud chưa nghiệm thu, báo đúng trạng thái và phương án local evidence. Không biến deadline thành lý do bỏ source/citation guards.

## Ước lượng còn lại — không phải cam kết

| Hạng mục sau review | Công sức dự kiến | Phụ thuộc |
|---|---:|---|
| Điền bìa, đối chiếu rubric và sửa văn phong |1–2 giờ | Thông tin/rubric thực tế |
| Xuất báo cáo, kiểm hình/bảng/reference/PDF |2–3 giờ | Mẫu định dạng và công cụ của sinh viên |
| Làm slide, rehearsal, gói source/evidence |2–3 giờ | Quyết định cách demo và kênh giao asset |
| Kiểm gói cuối, tải nộp, lưu biên nhận |0,5–1 giờ | Giờ nộp/hệ thống học phần |
| Release cloud: commit/CI/PG cloud/backup/public E2E |Ước lượng thêm 4–8 giờ nếu local preflight đạt | Phê duyệt, quyền cloud, restore/image và ngày nguồn |
| Model pilot mới hoặc full evaluation |Chưa ước lượng completion đáng tin | Budget cũ không đủ; cần quyết định riêng, quota, pháp lý và protocol |

Tối thiểu cho bản nộp học thuật từ bản thảo khoảng **5,5–9 giờ làm việc**; không cộng thời gian chờ quyền cloud/quota thành thời gian đã làm. Cloud deployment có thể chưa hoàn tất trước deadline nếu các phụ thuộc không giải quyết. Không cần tiếp tục tối ưu S06/C01 để hoàn thiện bản báo cáo trung thực.
