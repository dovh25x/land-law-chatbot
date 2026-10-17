# Kiến trúc và ranh giới dữ liệu

![Kiến trúc](diagrams/architecture.svg)

`frontend/src/App.tsx` quản lý hội thoại và SSE; `history.ts` chịu trách nhiệm IndexedDB. `frontend/functions/api/[[path]].ts` xác thực đường ingress bằng HMAC rồi chuyển tiếp tới Render. Backend gồm `api.py` (contract/quota/lease), `agent.py` (graph), `retrieval.py` và `store.py` (corpus/metadata), `provider.py` (Groq và usage).

## Một lượt hỏi

![Sequence chat](diagrams/chat-sequence.svg)

Client gửi tối đa 8 message lịch sử, tổng 12.000 ký tự. Lịch sử chỉ giải tham chiếu; citation cũ được kiểm tra ID và không thay thế retrieval mới. API kiểm tra phiên, quota, idempotency và lease. Agent lập kế hoạch một lần trước fallback, mở nguồn, synthesis rồi verify từng claim theo chủ thể/điều kiện/ngoại lệ/hệ quả/thời điểm. Chỉ kết quả cuối đi vào SSE.

Ngân sách: 6 request LLM gồm retry, 12 công cụ, 2 vòng retrieval, 1 repair, deadline 90 giây. Không đủ chứng cứ thì hỏi lại hoặc trả giới hạn. Bộ lọc claim phải tránh giữ câu phụ thuộc đoạn đã bị loại. Không tự nối điều kiện vào claim để vượt kiểm tra.

## Lưu trữ và bảo mật

IndexedDB: tối đa 20 cuộc, 40 message/cuộc, 10 MiB, 7 ngày từ khi tạo. Token phiên chỉ trong sessionStorage. Server giữ hash token, hash IP, counters, request fingerprint, trạng thái lượt và lease; không giữ body, answer cache hay trace chi tiết. Migration 006 xóa payload cũ và thu hồi quyền runtime; không tạo backup hội thoại.

Công cụ agent chỉ đọc và có schema: search_law, search_project, open_article, check_effectivity, normalize_place. Tài liệu và history không được phép ra lệnh thực thi SQL/shell/URL. Markdown không thực thi HTML. HMAC dùng IP do Cloudflare xác minh, không tin header IP từ người dùng.

## Corpus

![Vòng đời corpus](diagrams/corpus-lifecycle.svg)

Nguồn chính thức → parse/OCR ngoại tuyến → chunk theo locator/trang → metadata/checksum/quan hệ → E5 → snapshot → restore và publish. Contract `multilingual-e5-small-onnx-q8-window-v1`, 384 chiều; không đổi preprocessing hoặc embedding khi chỉ lọc dự án. SQLite và PostgreSQL có lexical backend khác nhau; báo cáo retrieval phải nêu backend.
