# Checklist nộp đồ án

Ngày 21/10/2026 (Việt Nam). Deadline thực hiện gói: trước 23:00 hôm nay; deadline học phần theo kế hoạch: 23/10/2026. Thông tin chưa có được để trống, không điền giả.

- [ ] Sinh viên điền họ tên, MSSV, lớp, mã/tên học phần, khoa và GVHD trên bìa/slide.
- [ ] Đối chiếu rubric và mẫu bìa chính thức nếu được cung cấp; hiện chưa có trong repo.
- [x] Có báo cáo Markdown/HTML/PDF tiếng Việt 12 chương và tài liệu tham khảo.
- [x] Có 12 slide PPTX/PDF; có source `slides.json` và script xuất.
- [x] Có evaluation summary, demo guide và known limitations, liên kết evidence gốc.
- [ ] Đọc lại PDF, thông tin hành chính và slide trên máy trình chiếu thực tế.
- [ ] Kiểm `asset-validation.json`, checksum và không có trang/slide thiếu tiếng Việt.
- [ ] Gửi đúng release SHA/manifest do release owner xác nhận; không dùng HEAD nền Phase 4 làm source release mới.
- [ ] Đối chiếu CI và deployment/public E2E với `delivery-status.json`; chỉ tuyên bố PASS khi có receipt.
- [ ] Kèm source, lockfiles, manifest, evaluation suites đã khóa và chỉ dẫn assets corpus/model có checksum.
- [ ] Quét secrets và kiểm archive cuối; loại `.env`, keys, DB thử nghiệm và dữ liệu cá nhân.
- [ ] Giữ mọi failure artifacts: S06 FAIL, C01 INCOMPLETE; không xóa/thay gold.
- [ ] Rehearsal 10 phút thuyết trình và 5 phút demo có nhãn rõ live/replay/fixture.
- [ ] Sao lưu gói PDF/PPTX/evidence manifest sang nơi nộp được giảng viên chỉ định.

Không cần thực hiện thêm model benchmark để gọi tài liệu là đã xuất. Các mục cloud/model chưa đạt phải được khai báo, không được đánh dấu hoàn thành nhờ fixture hoặc source-only demo. Nếu deployment bị chặn, nộp source đã test cùng evidence và bản demo nguồn được dán nhãn; không công khai generation không an toàn.

## Mode demo cuối đã chọn

- [x] Fallback source-only đã implement và kiểm API thật local, không gọi model.
- [x] Report/demo/slides phân biệt mode nguồn mới với phép đo RAG fingerprint cũ.
- [ ] Chốt full regression/image, Git SHA/CI và public E2E từ release owner; local PASS không thay cloud PASS.
- [ ] Demo đúng ngày được review: 21/10/2026 có 43 passages; 23/10 chỉ header, cần khai báo hoặc review mới có căn cứ, không tự gia hạn.
- [ ] Tái xuất PDF/PPTX sau khi có delivery-status cuối và đối chiếu checksum.
