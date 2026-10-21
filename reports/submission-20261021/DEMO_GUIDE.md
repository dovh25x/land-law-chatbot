# Demo MVP tra cứu nguồn đã review

**Chế độ candidate:** `SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`. Chỉ hiển thị đoạn nguyên văn và xuất xứ trong khoảng ngày đã review; không tạo đáp án AI hoặc kết luận quyền lợi. Backend/API SQLite và PostgreSQL16 riêng đã PASS local; cloud/public E2E xem [delivery-status.json](delivery-status.json), không tự coi đã đạt.

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
| 3 — 90 giây | Tìm theo tên/số hiệu “31/2024”, mở nguồn, xem locator Điều 95, 98 hoặc 108; mở URL gốc | Đọc nguyên văn một đoạn, không tự tạo kết luận hộ dân đủ điều kiện. Chỉ những đoạn hiện trong panel được review; toàn bộ văn bản không tự được đánh dấu đã xác minh. |
| 4 — 70 giây | Tìm “40/2026”, mở Điều 17 hoặc 21 được hiển thị; đối chiếu nguồn chính thức | Cho thấy quy định địa phương có nguồn/locator riêng, cần đọc cùng phần luật/nghị định; không kết luận mọi người đều được hỗ trợ hoặc được giao đất. |
| 5 — 50 giây | Chọn ngày 23/10/2026, nhấn đối chiếu | Local acceptance chỉ còn một header/Điều 2 của QĐ40, không đủ nguồn nghiệp vụ. Nói rõ “Phạm vi ngày 21 không tự gia hạn ngày 23.” Không đổi receipt hoặc bypass để có nhiều kết quả. |
| 6 — 40 giây | Đổi sang 02/08/2024 nếu cần, sau đó trở về 21/10/2026 | Có 25 passages lịch sử. Đọc đúng nhãn ngày; không trình luật lịch sử như hiện hành. |
| 7 — 50 giây | Reload, đổi kích thước mobile; nếu có history cũ, đọc cảnh báo trước khi xóa theo lựa chọn người dùng | Lịch sử chỉ nằm trên thiết bị trong 7 ngày. Citation cũ không được tái dùng như chứng cứ đã review cho hôm nay. Không tạo hội thoại giả để làm đầy history. |

Tình huống người dân “Nhà tôi chắc chắn được bao nhiêu tiền/được một suất không?” được giải thích bằng giới hạn sản phẩm: **mode này không trả lời câu hỏi quyền lợi**, chỉ hỗ trợ đọc nguồn. Không gọi một chat bị tắt là model clarification/refusal pass.

## 3. Giải thích evaluation trong demo — khoảng 1 phút

Mở [EVALUATION.md](EVALUATION.md) và [acceptance API thật](../release-final-20261021/qa/source-lookup-acceptance.json): 0 provider generate calls. Sau đó nếu cần, mở [retrieval cohort cũ](../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json): macro Recall@5 97,37% trên 19 câu SQLite; 20/21 chunks, micro 95,24%. Đây là tìm nguồn, không phải legal-answer accuracy hoặc benchmark mode source-only mới.

Giữ S06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN trong Phase 3A. C02 allocation độc lập mới INCOMPLETE: một HTTP 400, không có Draft hợp lệ; xem [QA pilot review](../release-final-20261021/qa/c02-pilot-review.md). Không trình draft lỗi như answer. C04/C05 có thể xem trong [capture fixture cũ](../phase3b-reliability-20261021T073924Z/synthesis-final/report.json) để giải thích nhánh hỏi thêm/từ chối của RAG; phải nói **FIXTURE**, không phải kết quả model hoặc public mode hiện tại.

## 4. Public E2E — cần bằng chứng riêng

Chỉ dùng URL và SHA trong delivery status/manifest đã xác minh. Kiểm frontend/source panel qua browser thật; request qua signed ingress, ngày áp dụng, link nguồn, reload, mobile và lỗi backend. Public source lookup PASS không xác nhận Turnstile/chat/follow-up generative đã hoạt động: những chức năng đó đang bị tắt, phải báo chưa kiểm hoặc không khả dụng trong mode này.

Không dùng `verify_live_ui.mjs --chat` cho bản demo này. Script lịch sử có hai lượt chat và `--source-only` không phải cờ đảm bảo zero-call trên runtime generative. Release owner cần dùng checks phù hợp mode nguồn; tuyệt đối không bật generation hoặc reset quota để vượt kịch bản. Không lưu session tokens, HMAC headers, credentials hoặc dữ liệu người dùng vào ảnh/log.

## 5. Dự phòng

- **Backend/cold start:** báo đang chờ Render, chờ có giới hạn; chuyển sang API receipt/screenshot thật nếu không sẵn sàng, ghi public demo chưa hoàn tất. Không coi thời gian cold start là model latency.
- **Nguồn gốc không mở/mất mạng:** trình snapshot/locator/checksum ngày review, nói đây là bản lưu; không xác nhận review mới.
- **429 hoặc dấu hiệu model được gọi:** dừng ngay; source-only demo phải có 0 model calls. Không đổi key/tài khoản hoặc bật chat.
- **Ngày không có coverage nghiệp vụ:** giữ kết quả hạn chế; trình historical/current review với ngày được công bố. Không đánh dấu fresh hàng loạt.
- **Cloud chưa deploy đúng candidate:** dùng LOCAL hoặc RECORDED EVIDENCE rõ nhãn, kèm source release/test; không đọc URL lịch sử như chứng nhận bản mới đã phát hành.
