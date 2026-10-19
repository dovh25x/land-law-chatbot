# Bỏ cảnh báo snapshot khỏi giao diện — 2026-10-19

Theo yêu cầu chủ dự án, không hiển thị câu “Nguồn chưa được rà soát cập nhật; nội dung tham khảo từ snapshot, chưa xác nhận quy định hiện hành...” trong giao diện hoặc lời mở đầu tự động của đáp án.

## Thay đổi

- Bỏ banner snapshot trên màn hình chat và phần bổ sung cảnh báo trong nhãn trạng thái bảng thông tin.
- Backend không chèn câu cảnh báo vào lời mở đầu khi cho phép generation trên snapshot.
- Với đáp án cũ đã lưu IndexedDB, frontend chỉ bỏ đúng tiền tố tự động khi hiển thị và sao chép. Không sửa nội dung lịch sử gốc, không lọc câu hỏi người dùng hoặc diễn giải/điều kiện pháp lý trong đáp án.
- API vẫn giữ source_fresh=false, warning=source_stale và source_checked_at thực tế. Ops/report vẫn phản ánh nguồn chưa rà soát. Không đổi checked_at, corpus, embedding, quota hoặc kiểm chứng claim/citation. Chế độ strict vẫn chặn generation khi nguồn cũ và không được cho phép dùng snapshot.
- Cập nhật tài liệu và chú thích diagram; SVG xuất bằng helper diagram-design revision đã ghim, self-check/geometry và xem trực quan.

## Kiểm chứng

Source thực hiện: `4c6494d57984df497df3d677489c122915a392a3`. Source cuối `f3f99722cfe1fb81c29607eda16055f3a1640ac4` chỉ sửa locator kiểm thử mobile; source runtime không đổi giữa hai commit. Fingerprint PostgreSQL: `d8a9ec26b9b72bf3ff58b224200fd70fdcb3bae6e6b29d2e39a563b49d895595`.

- Backend: 257 passed, gồm kiểm tra không chèn cảnh báo nhưng giữ freshness metadata và từ chối claim không được hỗ trợ.
- Frontend unit: 7 passed; build thành công; secret scan đạt.
- E2E local lần đầu: 77 passed, một lỗi locator của test mới vì mobile có hai nút cùng tên. Các assertion banner/đáp án cũ/reload đã đạt; lỗi ở bước chọn nút mở bảng thông tin. Sửa locator để chọn nút topbar; regression desktop/mobile đạt 2/2.
- CI cuối 39209962131: success, bao gồm toàn bộ 78 E2E, backend/unit/build/audit và Docker memory check. Giữ log và kết quả attempt đầu, không sửa báo cáo cũ thành passed.
- Deploy đầu 39209766116: success, giao diện production đã xác nhận không còn banner. Bản deploy cuối ghim source có regression locator đã sửa.

Không chạy lại suite đánh giá nội dung hoặc gọi LLM thật cho thay đổi lời mở đầu/giao diện này. Kiểm thử public chat qua managed Turnstile không được tuyên bố là đã thực hiện. Freshness chỉ được báo trong metadata, báo cáo này và các công cụ vận hành.

## Kiểm tra giao diện production

`live-ui.json` ghi nhận cả 1440, 390 và 320 px đạt: không có banner snapshot, bảng thông tin chỉ báo khả năng sinh đáp án. API vẫn báo `source_fresh=false`, `warning=source_stale`, generation khả dụng và fingerprint đúng source. Ảnh chụp được lưu cùng report; đã xem trực quan bản mobile. Không gửi câu hỏi thật hoặc tạo phiên Turnstile trong phép kiểm tra này.

CI source cuối: [39209962131](https://github.com/dovh25x/land-law-chatbot/actions/runs/39209962131). Deploy source cuối: [39209976619](https://github.com/dovh25x/land-law-chatbot/actions/runs/39209976619).

Deploy cuối đã success: Render `dep-dbarhdcs728c739dbsj0` live và verified đúng SHA `f3f99722cfe1fb81c29607eda16055f3a1640ac4`. Workflow xác minh corpus/fingerprint và navigation production thành công; receipt và ảnh nằm trong `workflow-evidence/`. Không thay đổi asset corpus hoặc database.
