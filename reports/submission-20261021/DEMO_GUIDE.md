# Demo MVP tra cứu nguồn đã review

**Chế độ candidate:** `SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`. Chỉ hiển thị đoạn nguyên văn và xuất xứ trong khoảng ngày đã review; không tạo đáp án AI hoặc kết luận quyền lợi. Backend/API SQLite và PostgreSQL 16 riêng PASS; [public source-only browser](../release-final-20261021/qa/public-source-2026-10-21T11-02-32-079Z/report.json) đã PASS đúng code ec5 trên [URL live](https://hanoi-land-law.pages.dev). Chỉ scope nguồn, không generative E2E; chi tiết [delivery-status.json](delivery-status.json).

Mục tiêu 5–7 phút. Không gửi thông tin thật, không gọi model, không chạy lại C01/S06/C02. Dùng ngày giả lập **21/10/2026**, giải thích đây là ngày tra cứu đã review, không đổi ngày trên máy để giả làm nguồn hiện hành.

## 1. Chọn đúng loại trình diễn

| Môi trường | Nhãn phải hiển thị/nói rõ | Điều kiện |
|---|---|---|
| Public URL | LIVE — verified source lookup | Chỉ sau khi release owner xác minh đúng SHA, corpus, source-only PG fingerprint và public E2E |
| API/UI local với corpus/receipts thật | LOCAL — verified source lookup | SQLite riêng, không key, mode nguồn bật; không phải cloud hoặc model demo |
| Mở report/capture đã lưu | RECORDED EVIDENCE / FIXTURE nếu có mock | Giữ fingerprint, ngày hỏi và nhãn; không giả thành UI live |

Baseline source-only SQLite fingerprint: `dba699954ac85068b40f676eaa2c927065d81c406eda7b08a6665ffafc53e58e`. PG fingerprint đã kiểm API read-only local: `8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464`; deployed identity phải được kiểm thực tế. RAG retrieval và C02 model thuộc fingerprint cũ `1697…`, không dùng làm quality score của mode mới.

## 2. Kịch bản chính — nguồn thật, không model

| Bước | Thao tác | Lời giải thích và kiểm chứng |
|---|---|---|
| 1 — 40 giây | Mở candidate và đọc banner; quan sát composer bị tắt | “Đây là bản thử nghiệm tra cứu đoạn nguồn đã review, không sinh đáp án pháp luật, không xác nhận quyền lợi cá nhân.” Nếu banner/mode sai hoặc vẫn gửi được chat, dừng live demo. |
| 2 — 50 giây | Bấm **Mở thư viện nguồn đã review**. Chọn ngày 21/10/2026 và **Đối chiếu ngày đã chọn** | API thật local có 7 documents / 43 passages. Đây là số đoạn trong receipt, không phải 43 quy tắc áp dụng cho mọi hồ sơ. |
| 3 — 90 giây | Tìm theo tên/số hiệu “31/2024”, mở nguồn, xem locator Điều 95, 98, 108 hoặc khoản 4 Điều 111; mở URL gốc | Đọc nguyên văn một đoạn, không tự tạo kết luận hộ dân đủ điều kiện. Chỉ những đoạn hiện trong panel được review; toàn bộ văn bản không tự được đánh dấu đã xác minh. |
| 4 — 70 giây | Tìm “40/2026”, mở Điều 17 hoặc 21 được hiển thị; đối chiếu nguồn chính thức | Cho thấy quy định địa phương có nguồn/locator riêng, cần đọc cùng phần luật/nghị định; không kết luận mọi người đều được hỗ trợ hoặc được giao đất. |
| 5 — 50 giây | Chọn ngày 23/10/2026, nhấn đối chiếu | Local acceptance chỉ còn một header/Điều 2 của QĐ 40, không đủ nguồn nghiệp vụ. Nói rõ “Phạm vi ngày 21 không tự gia hạn ngày 23.” Không đổi receipt hoặc bypass để có nhiều kết quả. |
| 6 — 40 giây | Đổi sang 02/08/2024 nếu cần, sau đó trở về 21/10/2026 | Có 25 passages lịch sử. Đọc đúng nhãn ngày; không trình luật lịch sử như hiện hành. |
| 7 — 50 giây | Reload, đổi kích thước mobile; nếu có history cũ, đọc cảnh báo trước khi xóa theo lựa chọn người dùng | Lịch sử chỉ nằm trên thiết bị trong 7 ngày. Citation cũ không được tái dùng như chứng cứ đã review cho hôm nay. Không tạo hội thoại giả để làm đầy history. |

Tình huống người dân “Nhà tôi chắc chắn được bao nhiêu tiền/được một suất không?” được giải thích bằng giới hạn sản phẩm: **mode này không trả lời câu hỏi quyền lợi**, chỉ hỗ trợ đọc nguồn. Không gọi một chat bị tắt là model clarification/refusal pass.

### Mapping ba chủ đề demo tới các đoạn đã review

Không tạo đáp án quyền lợi mới. Nếu đọc câu hỏi, lấy nguyên văn và giả định từ [case khóa Phase 2C](../phase2c-current-20261021/acceptance-cases-final.json), không sửa gold hoặc rút bỏ điều kiện.

| Case/chủ đề | Tên/số hiệu để tìm trong thư viện | Locator cần đối chiếu trong phần hiển thị |
|---|---|---|
| C01 — bồi thường | Luật 31/2024 và NQ 254/2025 | Điều 95, 98; phần liên quan Điều 3/13 đã review; không quyết định hộ được hình thức/số tiền cụ thể |
| C02 — hỗ trợ | Luật 31/2024, QĐ 40/2026, NĐ 49/2026 | Điều 108; QĐ 40 Điều 17; NĐ 49 Điều 11 và các đoạn phụ thuộc được hiển thị |
| C03 — tái định cư | Luật 31/2024, NĐ 88/2024, NĐ 226/2025, NĐ 49/2026, QĐ 40/2026 | Khoản 4 Điều 111; NĐ 88 Điều 11; phần scoped NĐ 226 Điều 7 và NĐ 49 Điều 16; QĐ 40 Điều 21 |

C03 phải đọc đúng nhánh/scoped excerpt, không coi toàn bộ điều hoặc văn bản đã được review. [Negative source checks public](../release-final-20261021/public-source-rejections.json) xác nhận NĐ 71 chưa review bị 404 và ngày 29/10 không có passages. Có thể cho xem receipt hoặc chọn ngày 29/10 trên UI như ví dụ ngoài phạm vi; đó không phải model refusal hoặc thay một case evaluation thất bại.

## 3. Giải thích evaluation trong demo — khoảng 1 phút

Mở [EVALUATION.md](EVALUATION.md) và [acceptance API thật](../release-final-20261021/qa/source-lookup-acceptance.json): 0 provider generate calls. Sau đó nếu cần, mở [retrieval cohort cũ](../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json): macro Recall@5 97,37% trên 19 câu SQLite; 20/21 chunks, micro 95,24%. Đây là tìm nguồn, không phải legal-answer accuracy hoặc benchmark mode source-only mới.

Giữ S06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN trong Phase 3A. C02 allocation độc lập mới INCOMPLETE: một HTTP 400, không có Draft hợp lệ; xem [QA pilot review](../release-final-20261021/qa/c02-pilot-review.md). Không trình draft lỗi như answer. C04/C05 có thể xem trong [capture fixture cũ](../phase3b-reliability-20261021T073924Z/synthesis-final/report.json) để giải thích nhánh hỏi thêm/từ chối của RAG; phải nói **FIXTURE**, không phải kết quả model hoặc public mode hiện tại.

## 4. Public E2E — cần bằng chứng riêng

URL live đã kiểm là https://hanoi-land-law.pages.dev, application SHA ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec. Chỉ dùng identity/corpus đã xác minh trong manifest. Kiểm frontend/source panel qua browser thật; request qua signed ingress, ngày áp dụng, link nguồn, reload, mobile và lỗi backend. Public source lookup PASS không xác nhận Turnstile/chat/follow-up generative đã hoạt động: những chức năng đó đang bị tắt, phải báo chưa kiểm hoặc không khả dụng trong mode này.

Không dùng `verify_live_ui.mjs --chat` cho bản demo này. Script lịch sử có hai lượt chat và `--source-only` không phải cờ đảm bảo zero-call trên runtime generative. Release owner cần dùng checks phù hợp mode nguồn; tuyệt đối không bật generation hoặc reset quota để vượt kịch bản. Không lưu session tokens, HMAC headers, credentials hoặc dữ liệu người dùng vào ảnh/log.

## 5. Dự phòng

- **Backend/cold start:** báo đang chờ Render, chờ có giới hạn; chuyển sang API receipt/screenshot thật nếu không sẵn sàng, ghi public demo chưa hoàn tất. Không coi thời gian cold start là model latency.
- **Nguồn gốc không mở/mất mạng:** trình snapshot/locator/checksum ngày review, nói đây là bản lưu; không xác nhận review mới.
- **429 hoặc dấu hiệu model được gọi:** dừng ngay; source-only demo phải có 0 model calls. Không đổi key/tài khoản hoặc bật chat.
- **Ngày không có coverage nghiệp vụ:** giữ kết quả hạn chế; trình historical/current review với ngày được công bố. Không đánh dấu fresh hàng loạt.
- **Cloud chưa deploy đúng candidate:** dùng LOCAL hoặc RECORDED EVIDENCE rõ nhãn, kèm source release/test; không đọc URL lịch sử như chứng nhận bản mới đã phát hành.

## Tái lập sau khi receipts hết hạn

Archived receipts chỉ xác nhận scope/ngày đã review, không chứng minh freshness vô thời hạn. Live import yêu cầu review gần đây (không quá 7 ngày). Restore có thể khớp byte/checksum nhưng activation vẫn phải có review mới hợp lệ nếu hết hạn; không sửa `checked_at`, tự gia hạn hoặc bypass F01. Ngày22/23 có thể chọn rõ **21/10/2026 như historical as_of**, không gọi đó là coverage hiện hành ngày 23. Release này không bổ sung coverage nghiệp vụ cho 22/23.
