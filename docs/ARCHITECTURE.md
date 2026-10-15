# Thiết kế kỹ thuật

## Luồng dữ liệu
Nguồn chính thức → tải/parse HTML, PDF và OCR ngoại tuyến → chia đoạn theo điều/khoản/trang → metadata/checksum/quan hệ → E5 → snapshot corpus → PostgreSQL/pgvector. React gọi FastAPI; backend chạy LangGraph và Groq. Không tải model sinh hoặc OCR trên Render.

Corpus `corpus-de584c31fc95f9a2`: 69 tài liệu, 54 văn bản pháp luật và 15 nguồn thông tin dự án, 7.610 vector. Manifest: `data/sources.json`; quan hệ: `data/legal_relations.json`; địa bàn: `data/place_aliases.json`. Nguồn gốc và ngày kiểm tra nằm trong từng văn bản. Tin dự án không chứng minh quyền lợi hộ hoặc tình trạng thửa.

## Retrieval và agent
PostgreSQL full-text cấu hình simple, hỗ trợ tìm không dấu, kết hợp vector bằng RRF; ưu tiên số hiệu/điều và mở đoạn liên quan. SQLite dùng nhánh tìm kiếm local phù hợp demo. Tài liệu trung ương vẫn được giữ khi lọc Vành đai 4.

Graph: plan → tools → synthesize → verify → finish; khi cần có truy xuất bổ sung hoặc sửa đáp án. Công cụ chỉ đọc: search_law, search_project, open_article, check_effectivity, normalize_place. Không có SQL/shell/URL tùy ý. Không phát nội dung đáp án trước bước verify. Trace chỉ ghi sự kiện/công cụ/tài liệu, không hiển thị suy nghĩ nội bộ.

Giới hạn mỗi lượt: 6 request LLM (gồm retry), 12 công cụ, 2 vòng retrieval, 90 giây. Groq là provider duy nhất; E5 ONNX Q8 dùng cùng model/preprocessing cho query và corpus. Metadata model được ghim để không trộn vector.

## API
- POST /api/v1/sessions: phiên/token.
- POST /api/v1/chat: session_id, message, project tùy chọn, as_of tùy chọn; SSE progress rồi result. Chỉ mode agentic được hỗ trợ; baseline bị từ chối.
- GET /api/v1/sessions/{id}/messages và /api/v1/sessions/{id}/traces/{trace_id}: cần token phiên.
- GET /api/v1/documents và /api/v1/documents/{id}: nguồn công khai.
- GET /api/v1/projects: chỉ Vành đai 4.
- GET /api/v1/evaluations/latest: báo cáo, release và fingerprint khớp/không khớp.
- GET /healthz, /readyz: tình trạng backend, corpus và dependency.

Câu hỏi riêng về Sông Hồng/Olympic được chặn ngoài phạm vi trước khi gọi LLM. Tài liệu vẫn ở thư viện. Trạng thái công bố luôn là nguyên mẫu học thuật, không có nghiệm thu pháp lý. Các khóa publication cũ chỉ được đọc để tương thích snapshot; không còn lệnh cấp accepted.

## Bảo mật và giới hạn
Token phiên ngẫu nhiên lưu hash; tách phiên, TTL 7 ngày; log vận hành không chứa nguyên câu hỏi hoặc secret. 3 lượt/phút theo IP và phiên, 20 lượt/ngày mỗi phiên, tối đa 2 lượt đang xử lý. Không có trần chat ngày theo IP chung và không có quota LLM nội bộ theo ngày. Provider vẫn áp quota riêng. CORS cho frontend, Markdown không thực thi HTML. Chỉ nhập dữ kiện đã ẩn danh.

Kiểm tra nguồn/ngày/điều khoản là biện pháp kỹ thuật, không bảo đảm đúng pháp lý toàn diện. Khi thiếu hoặc cũ, câu trả lời phải nêu giới hạn; không tự suy quyền lợi cá nhân.
