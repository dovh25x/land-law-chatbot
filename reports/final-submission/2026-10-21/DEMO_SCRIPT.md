# Kịch bản demo có kiểm chứng

Mục tiêu: 5–7 phút, không gọi Groq trong Phase 4. Không có câu trả lời RAG từ model thật được xác nhận trên runtime cuối. Vì vậy demo mặc định là **replay evidence nguồn/retrieval và fixture được ghi nhãn**, không giả làm một hội thoại live thành công. Không phát draft C01/S06 như đáp án đã verify.

## Chuẩn bị

- Mở [evaluation summary](EVALUATION_SUMMARY.md), [final retrieval receipt](../../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json), [context capture](../../phase3b-reliability-20261021T073924Z/synthesis-final/report.json), [legal review](../../phase2c-current-20261021/LEGAL_REVIEW.md) và [case khóa](../../phase2c-current-20261021/acceptance-cases-final.json).
- Mở nguồn chính thức theo URL trong legal review nếu mạng truy cập được; bản snapshot local chỉ là bằng chứng đã lưu, không được thay bằng dấu “đã kiểm mới”.
- Ghi rõ ngày pháp lý của từng case, runtime fingerprint và nhãn **RECORDED / FIXTURE / NOT MODEL** trên cửa sổ trình bày.
- Không dùng tài khoản/hồ sơ thật. Không reset quota, retry case thất bại hoặc bấm gửi chat trên cloud trong buổi chuẩn bị chưa được duyệt.

## Kịch bản mặc định

| Bước | Thao tác | Điều có thể nói và điều kiện dừng |
|---|---|---|
| 1 — 40 s | Giới thiệu scope và thông báo hạn chế | “Đây là tra cứu Vành đai 4 Hà Nội, không tính tiền hoặc xác định quyền của hộ dân.” |
| 2 — 90 s | Mở đúng C02 từ case khóa; chỉ đọc câu hỏi/giả định, không tự đổi thành hồ sơ khác | Hiển thị các đoạn Điều 108, QĐ 40 Điều 17 và nguồn phụ thuộc trong capture; 3/3 units, 5.070 ký tự. Đây là context completeness, chưa phải đáp án model. |
| 3 — 60 s | Mở một hàng retrieval cùng gold IDs/top 5 trong receipt | Giải thích macro 19 câu và 20/21 hits; cho thấy N03 có miss. Không bấm chạy lại evaluation. |
| 4 — 60 s | Mở quote fixture cuối trong startup receipt | Có một claim/một citation trích từ nguồn đã review và actual snapshot; **fixture cả generation/judge**, không model RAG. Mở đúng văn bản/locator để kiểm chứng trích dẫn. Nếu không thể hiển thị artifact đúng checksum, bỏ bước, không đọc đáp án tự viết. |
| 5 — 50 s | Mở C04 thiếu dữ kiện trong receipt fixture/capture | Nhánh clarification; giải thích dữ kiện đất/giấy tờ/ngày phương án quyết định. Receipt coverage `8051…` và final capture `1697…` có phạm vi khác; không gọi đây là live model final. |
| 6 — 50 s | Mở C05 ngoài phạm vi hoặc C06 unreviewed | Chỉ ra status insufficient_evidence và không có legal claim được phát hành. Refusal của ca answerable không tự chấm đúng. |
| 7 — 50 s | Mở Phase 3A/S06 failure summaries và release checklist | Nói rõ C01 INCOMPLETE, C02/C03 NOT RUN, S06 FAIL. Cloud tuple/public E2E chưa đủ evidence; kết luận theo checklist, không theo mong muốn. |

Không có transcript mới trong tài liệu này. Mọi câu hỏi/đầu ra cần lấy nguyên văn từ artifact được dẫn, giữ locator/citation gốc. Nếu slide cần ảnh, chụp artifact thật kèm nhãn cohort, không dựng ảnh giả của câu trả lời live.

## Nếu muốn demo UI local

Chỉ sau khi người trình bày tự xác nhận cấu hình private local: SQLite mới, cả `DATABASE_URL` và `ADMIN_DATABASE_URL` rỗng, không key, generation tắt; không dùng `.env` production hoặc sửa `.env` chung. Dùng UI source-library/fixtures đã có, ghi rõ chế độ. Việc mở giao diện không chứng minh đã triển khai candidate trên cloud. Playwright fixture video/screenshot chỉ trình bày khi có file thật và nêu API mocked; không tạo video trả lời RAG giả.

## Kiểm thử public E2E sau phê duyệt deploy

Đây là hướng dẫn **chưa thực thi**, không phải status PASS. Trước hết cần candidate commit/image/corpus/receipt tuple đã kiểm, PG runtime fingerprint được xác minh, source scope phù hợp ngày demo, ingress/Turnstile/quota cấu hình thực và rollback đã thử cách ly.

1. Xác minh nguồn build và deployed corpus/fingerprint qua giao diện/readiness; không nhận một `/healthz=200` là đủ.
2. Navigation-only bằng `scripts/verify_live_ui.mjs` không gửi chat; kiểm URL frontend/backend đúng, consent/error/source library/responsive theo script. Giá trị fingerprint phải lấy từ PG candidate đã kiểm, không từ default SQLite/.env.
3. Chỉ khi được duyệt API budget riêng mới thử chat. Script `--chat` có **hai lượt chat**; ngay cả `--source-only` vẫn có follow-up có thể gọi LLM. Không mô tả cờ này là zero-call. Không dùng ngân sách còn 7.841 để tự bắt đầu C02 cần reservation 19.788.
4. Lưu ảnh/console/network metadata đã lọc, request counts/usage, commit/corpus/fingerprint và kết quả từng bước. Citation phải mở đúng nội dung/version, không chỉ trang văn bản gần giống.
5. Nếu thất bại: ghi FAIL/INCOMPLETE theo evidence, giữ log; không tự đổi model/guard/receipt hoặc phát draft để demo tiếp.

Mẫu lệnh navigation-only cho người vận hành **sau khi được phép**, không chạy trong Phase 4:

```bash
# Điền URL public và fingerprint PG đã xác minh; không chứa secret.
LIVE_BASE_URL='https://<frontend-candidate>' \
LIVE_EXPECTED_CORPUS='corpus-1afca764aa6692e0' \
LIVE_EXPECTED_CONFIGURATION='<verified-pg-runtime-fingerprint>' \
node scripts/verify_live_ui.mjs
```

Đối chiếu corpus ID trong metadata và báo cáo, dùng `LIVE_EXPECTED_CORPUS` để script bắt sai release. Đối chiếu tên biến/script tại thời điểm thực hiện; không in Turnstile/session tokens, headers ký ingress hoặc secrets ra slide/log công khai.

## Dự phòng

- **429/quota/cooldown:** dừng chat, hiển thị trạng thái thực và chuyển sang source/retrieval evidence đã lưu; không xoay key/tài khoản và không bấm lại liên tục.
- **Render cold start:** báo đang chờ dịch vụ, giới hạn một cửa sổ kiểm tra; không diễn giải cold start thành model latency. Nếu chưa sẵn sàng, dùng local evidence và ghi cloud chưa demo.
- **Mất mạng/nguồn không mở:** trình snapshot và checksum, nói là bản lưu ngày review; không tuyên bố đã kiểm hiệu lực mới.
- **UI/candidate chưa deploy:** thuyết trình kiến trúc + artifacts; checklist vẫn NOT READY. Demo fallback minh bạch là kết quả chấp nhận được của báo cáo, không phải thay bằng live success.
