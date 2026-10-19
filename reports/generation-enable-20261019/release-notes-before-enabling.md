Phát hành toàn bộ corpus Vành đai 4 đã tuyển chọn: **60 tài liệu, 7.392 đoạn**, corpus `corpus-a26bc99e541fbbe2`.

Bản phát hành học thuật được vận hành ở chế độ **tra cứu thư viện tài liệu; sinh câu trả lời AI bị khóa bằng `GENERATION_ENABLED=false`**. Người vận hành đã yêu cầu phát hành theo ngoại lệ dù báo cáo readiness vẫn `false`. Đây không phải chứng nhận chất lượng pháp lý hoặc kết quả kiểm thử đạt.

- Mã deploy đã kiểm thử: `6ca8f12f0d770f2076de20f0d070460894bd0bc8`. Commit đóng gói `f63ba8709bec42726c247a228c2cd7a3b70438e8` chỉ bổ sung bằng chứng so với mã này.
- Backend 248 tests đạt; frontend unit, build và 68 E2E đạt. Restore và retrieval đã kiểm tra riêng trên SQLite/PostgreSQL. Đã tải lại asset từ URL công khai không xác thực, đối chiếu checksum và restore riêng trên SQLite/PostgreSQL. Runtime role, session lease và cấm ghi messages/traces/answer cache đều đạt tại database mới trước khi chuyển kết nối phục vụ.
- Còn thiếu coverage, freshness và chất lượng câu trả lời theo các suite khóa; không sửa các kết quả thất bại thành đạt. Bảy nguồn đang chờ OCR/duyệt không nằm trong dữ liệu phục vụ. Chỉ tài liệu đã tuyển chọn thuộc Vành đai 4 và luật chung liên quan được phát hành.
- Giữ model Groq GPT-OSS 120B, E5 ONNX Q8 384 chiều và hosting Free. Không re-embed dữ liệu cũ; không lưu hội thoại hoặc trace chi tiết trên server.
- Giữ nguyên Release và corpus cũ để rollback. Không drop database, không restore đè database phục vụ.

`corpus-backup.json` chỉ chứa corpus/config; `manifest.json` và `SHA256SUMS` xác định byte của package. `readiness-before-exception.json` và `operator-exception.json` ghi rõ phạm vi chưa đạt và ngoại lệ được yêu cầu. Trạng thái working tree khi đóng gói được giữ đúng trong manifest; thay đổi chưa commit chỉ là artifact vận hành.

SHA-256 corpus backup: `204547346cf550e75ae165956cf3dc8dd19264da301876f80e725c39529069b2`.

Hồ sơ triển khai đã commit: [bằng chứng, giới hạn và rollback](https://github.com/dovh25x/land-law-chatbot/blob/87c5e8b01310b1d6f7e66752eed96c31813783f4/reports/restricted-release-20261019/README.md).

