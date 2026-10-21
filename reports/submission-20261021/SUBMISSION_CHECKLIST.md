# Checklist nộp đồ án

Ngày 21/10/2026 (Việt Nam). Deadline thực hiện gói: trước 23:00 hôm nay; deadline học phần theo kế hoạch: 23/10/2026. Thông tin chưa có được để trống, không điền giả.

- [ ] Sinh viên điền họ tên, MSSV, lớp, mã/tên học phần, khoa và GVHD trên bìa/slide.
- [ ] Đối chiếu rubric và mẫu bìa chính thức nếu được cung cấp; hiện chưa có trong repo.
- [x] Có báo cáo Markdown/HTML/PDF tiếng Việt 12 chương và tài liệu tham khảo.
- [x] Có 12 slide PPTX/PDF; có source `slides.json` và script xuất.
- [x] Có evaluation summary, demo guide và known limitations, liên kết evidence gốc.
- [ ] Đọc lại PDF, thông tin hành chính và slide trên máy trình chiếu thực tế.
- [x] Kiểm `asset-validation.json`, checksum, font nhúng, Vietnamese text và không trang/slide trắng.
- [ ] Gửi đúng release SHA/manifest do release owner xác nhận; không dùng HEAD nền Phase 4 làm source release mới.
- [x] Đối chiếu CI và public source-only scope với `delivery-status.json`; không generative E2E.
- [ ] Kèm source, lockfiles, manifest, evaluation suites đã khóa và chỉ dẫn assets corpus/model có checksum.
- [ ] Quét secrets và kiểm archive cuối; loại `.env`, keys, DB thử nghiệm và dữ liệu cá nhân.
- [x] Giữ mọi failure artifacts: S06 FAIL, C01/C02 INCOMPLETE và public/CI failures; không xóa/thay gold.
- [ ] Rehearsal 10 phút thuyết trình và 5 phút demo có nhãn rõ live/replay/fixture.
- [ ] Sao lưu gói PDF/PPTX/evidence manifest sang nơi nộp được giảng viên chỉ định.

Không cần thực hiện thêm model benchmark để gọi tài liệu là đã xuất. Các mục cloud/model chưa đạt phải được khai báo, không được đánh dấu hoàn thành nhờ fixture hoặc source-only demo. Nếu deployment bị chặn, nộp source đã test cùng evidence và bản demo nguồn được dán nhãn; không công khai generation không an toàn.

## Mode demo cuối đã chọn

- [x] Fallback source-only đã implement và kiểm API thật local, không gọi model.
- [x] Report/demo/slides phân biệt mode nguồn mới với phép đo RAG fingerprint cũ.
- [x] Full 529/16/110, image 381,80 MiB, exact ec5 CI và public source-only scope PASS; mọi failures giữ riêng.
- [ ] Demo đúng ngày được review: 21/10/2026 có 43 passages; 23/10 chỉ header, cần khai báo hoặc review mới có căn cứ, không tự gia hạn.
- [x] Tái xuất PDF/PPTX sau delivery-status cuối; validator/provenance/checksum PASS.

## Chốt source và đóng gói

- [x] Candidate code cuối đã commit/push: `ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec`.
- [x] Main/release cùng SHA ec5d9a9; CI run 39588182288 PASS exact SHA.
- [x] Deployed tuple ec5/8ee1/corpus 1afc và public source-only browser PASS; không full generative E2E.
- [x] Chốt delivery-status, build/export/validate PASS; ZIP được kiểm bằng `package_submission.py` và receipt riêng.
- [ ] So sánh hash PDF/PPTX trong `DELIVERABLES_SHA256.json` với asset upload thực tế.
- [ ] Kiểm ZIP giải nén vào thư mục riêng, không `.env`/DB/backups/credentials; giao source release/corpus asset/checksum theo manifest riêng.
- [ ] Giữ thông tin tài liệu sau code SHA ở manifest gói; không dùng document-only commit để ngụy nhận runtime mới đã deploy.
