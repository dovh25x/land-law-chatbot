# Kiến trúc hệ thống

## Tổng quan

![Kiến trúc hệ thống](diagrams/architecture.svg)

Ứng dụng tách ba luồng: chuẩn bị corpus ngoại tuyến, xử lý câu hỏi theo request và lưu hội thoại tại trình duyệt. Runtime không ingest hoặc OCR trong lúc phục vụ chat.

| Thành phần | Implementation | Trách nhiệm |
|---|---|---|
| Giao diện | `frontend/src/` | Hội thoại, nguồn, trace và lịch sử IndexedDB |
| Ingress | `frontend/functions/` | Chuyển tiếp SSE, lấy IP tại Cloudflare và ký request tới Render |
| API | `backend/landlaw/api.py` | Phiên, validation, quota, lease và vòng đời SSE |
| Agent | `backend/landlaw/agent.py` | Điều phối truy xuất, tạo draft và kiểm chứng |
| Provider | `backend/landlaw/provider.py` | Groq, retry trong ngân sách và ghi nhận usage |
| Retrieval/store | `retrieval.py`, `store.py` | Hybrid search, quan hệ văn bản, corpus và metadata thực thi |
| Corpus ngoại tuyến | `ingest.py`, `scripts/` | Parse/OCR, chuẩn hóa, kiểm tra và đóng gói snapshot |

## Vòng đời một lượt hỏi

![Trình tự xử lý chat](diagrams/chat-sequence.svg)

1. Client tạo UUID `request_id`, chọn các cặp hội thoại gần nhất và gửi tới API cùng origin.
2. Cloudflare Function ký request; backend xác thực ingress, bearer token và các giới hạn đầu vào.
3. API kiểm tra quota, lấy slot xử lý và tạo lease. Request ID đã sử dụng không được chạy lại.
4. Agent giải tham chiếu từ history và xác định phạm vi. Các trường hợp đủ điều kiện có thể được xử lý theo quy tắc; không phải mọi lượt đều gọi LLM.
5. Planner đề xuất truy xuất. Công cụ tìm kiếm, mở điều khoản và kiểm tra quan hệ cung cấp chứng cứ cho synthesis.
6. Verifier kiểm tra chủ thể, điều kiện, ngoại lệ, hệ quả và thời điểm. Claim không được hỗ trợ phải được sửa trong ngân sách hoặc loại bỏ, kể cả phần phụ thuộc bị mất ngữ cảnh.
7. API phát kết quả cuối qua SSE. Frontend lưu nội dung, citation và trace trong IndexedDB; server chỉ kết thúc metadata của lượt.

`progress` phản ánh sự kiện thực thi quan sát được. Draft và suy nghĩ nội bộ không được phát ra client. Contract chi tiết nằm trong [API](API.md).

### Agent flow

![Agent flow](diagrams/agent-flow.svg)

Retry truy xuất được ưu tiên trước repair. Tới `finish` không đồng nghĩa đã đủ chứng cứ: nếu verifier còn `issues`, còn `needs_more_evidence` hoặc không duyệt đủ claim, toàn bộ nhóm claim và citation bị loại. Giới hạn hiệu lực phải được kiểm tra ngay trong claim; `finish` không tự nối điều kiện pháp lý sau verify.

Xem [phân tích và sơ đồ agent chi tiết](AGENT_FLOW.md) cho nhánh quy tắc không gọi LLM, điều kiện ngân sách, cổng phát hành và giới hạn của thiết kế.

## Ngân sách và kiểm soát thực thi

| Giới hạn mỗi lượt | Giá trị |
|---|---:|
| Request LLM, gồm retry | 6 |
| Lần gọi công cụ | 12 |
| Vòng retrieval | 2 |
| Lần repair | 1 |
| Deadline backend, gồm xử lý DB và agent | 90 giây |

Planner có tối đa một request trước fallback. Runtime giữ một lượt đang chạy cho mỗi phiên và hai lượt đồng thời toàn hệ thống. Lease có thời hạn để giải phóng phiên khi worker chết; lease không cung cấp khả năng replay đáp án.

Khi hết ngân sách hoặc thiếu chứng cứ, hệ thống trả giới hạn thay vì giữ kết luận chưa được hỗ trợ. Không tự gắn thêm điều kiện vào claim để làm claim vượt kiểm chứng.

## Truy xuất và embedding

Hybrid retrieval kết hợp từ khóa, vector, tiêu đề và viện dẫn bằng RRF. Từ khóa hỗ trợ số hiệu và điều khoản; vector hỗ trợ cách diễn đạt tự nhiên. Các công cụ chỉ đọc gồm `search_law`, `search_project`, `open_article`, `check_effectivity` và `normalize_place`.

Query và corpus dùng cùng contract `multilingual-e5-small-onnx-q8-window-v1`, E5 ONNX Q8 384 chiều và preprocessing đã ghim trong `local_embedding.py`. Lọc corpus theo phạm vi không làm thay đổi embedding của chunk được giữ lại.

SQLite và PostgreSQL có lexical backend khác nhau. Vì vậy storage backend tham gia fingerprint và phải được ghi trong báo cáo; kết quả retrieval của hai backend không tự tương đương.

## Lưu trữ và quyền riêng tư

| Vị trí | Dữ liệu | Vòng đời |
|---|---|---|
| IndexedDB | Hội thoại, đáp án, citation, trace | 7 ngày từ khi tạo; tối đa 20 cuộc, 40 message/cuộc, tổng 10 MiB |
| `sessionStorage` hoặc bộ nhớ tab khi bị chặn | Bearer token phiên API | Theo vòng đời storage/tab; tách khỏi lịch sử dài hạn |
| Database backend | Corpus, hash token/IP, counters, fingerprint request, trạng thái và lease | Corpus có phiên bản; metadata được cleanup theo chính sách |
| Log ứng dụng | Request ID, kết quả, lỗi theo loại, latency và usage | Theo cấu hình lưu log của hosting |
| Corpus backup | Snapshot và cấu hình công khai cần khôi phục | Theo Release và quy trình vận hành |

Server không lưu messages, answer cache hoặc trace chi tiết giữa các lượt. Migration 006 xóa payload cũ và thu hồi quyền runtime trên các bảng đó. Nội dung vẫn được xử lý trong bộ nhớ và truyền tới Groq; lịch sử chỉ ở client không đồng nghĩa nội dung không rời thiết bị.

## Ranh giới tin cậy

- Browser input, lịch sử và tài liệu đều là dữ liệu không đáng tin. Chúng không được cấp quyền thực thi SQL, shell hoặc URL tùy ý.
- Citation cũ chỉ giúp xác định ngữ cảnh. Kết luận mới phải có chứng cứ được truy xuất và kiểm tra lại.
- Cloudflare là ingress tin cậy để xác định IP và ký HMAC. Backend production từ chối API request không có chữ ký hợp lệ; không tin IP do client tự khai báo.
- Turnstile được xác minh server-side khi tạo phiên. Chỉ số hoặc header do client gửi không thể chuyển usage sang operator.
- Markdown không thực thi HTML. Credentials không xuất hiện trong `VITE_*`, response hoặc log nội dung.

Chi tiết cấu hình và xử lý sự cố nằm trong [vận hành](OPERATIONS.md).

## Vòng đời corpus

![Vòng đời corpus](diagrams/corpus-lifecycle.svg)

Nguồn chính thức được parse hoặc OCR ngoại tuyến, chia chunk theo điều/khoản/trang và gắn checksum, locator, ngày kiểm tra cùng quan hệ văn bản. Snapshot chỉ chuyển active sau khi kiểm tra phạm vi, tính toàn vẹn và restore riêng thành công.

Corpus vận hành chỉ gồm Vành đai 4 và luật chung liên quan. Không rollback sang corpus đa dự án hoặc phiên bản ghi hội thoại lên server. Các lựa chọn kiến trúc và hệ quả được lưu trong [ADR](adr/README.md).

Danh mục `catalog.py` chỉ cung cấp provenance và liên kết bản gốc chưa lập chỉ mục cho thư viện. Nó không thêm pipeline retrieval, không thay đổi corpus hoặc embedding và không cấp chứng cứ cho synthesis.
