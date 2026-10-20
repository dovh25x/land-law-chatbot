# Bản đồ công nghệ và công cụ đã khảo sát

Đây là mô tả source tại SHA trong [inventory](source-inventory.json), không phải kiểm tra các cấu hình tài khoản bên ngoài hoặc xác nhận mọi dependency đang được dùng ở mọi request.

| Lớp | Công nghệ/công cụ | Vai trò và lưu ý |
|---|---|---|
| Web | React 19, TypeScript, Vite 6, CSS/tokens hiện có, plugin Tailwind | SPA với hội thoại, thư viện, evaluation; không có lựa chọn model hoặc upload hồ sơ |
| Hiển thị | Be Vietnam Pro, Lucide, react-markdown, responsive drawer/modal | Nguồn và trace của đúng đáp án, focus/IME/theme, chặn HTML; phần chat không biến link model thành thao tác mạng tùy ý |
| Lưu phía client | IndexedDB; sessionStorage và memory fallback | Nội dung/citation/trace tối đa 7 ngày; token phiên tách riêng; theme localStorage không chứa hội thoại |
| Ingress | Cloudflare Pages Functions, Web Crypto HMAC/SHA-256, Turnstile | Cùng origin, upstream cố định, ký method/path/query/time/IP/body; backend xác minh challenge và chữ ký |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic/Pydantic Settings, asyncio | Validation, sessions, counters/lease, deadline, SSE chỉ progress và kết quả đã verify |
| Điều phối | LangGraph StateGraph | Một graph plan/tools/synthesize/verify/repair/finish; không memory/checkpointer lưu hội thoại server |
| LLM | Groq HTTP API qua httpx, GPT-OSS 120B, structured JSON schema | Output Pydantic, tool_choice none; tool descriptor là dữ liệu cho ứng dụng, không remote function execution |
| Embedding | E5 small ONNX Q8, onnxruntime, sentencepiece, NumPy | 384 chiều, model/tokenizer revision và hash ghim; prefix/window/pooling/normalization cùng contract; một inference có lock |
| Retrieval | RRF của lexical/vector/heading/exact-reference/replacement candidates | Top-8 và mở rộng parent/relations có giới hạn; query đời thường được hỗ trợ một phần; không reranker |
| Dữ liệu production | PostgreSQL, pgvector HNSW 384, GIN tsvector, unaccent, psycopg/pool | TLS, runtime role/RLS, transaction lease/counters; migration cũ giữ lịch sử schema không có nghĩa runtime còn dùng model/vector cũ |
| Local | SQLite WAL và lexical implementation riêng | Không có tương đương retrieval mặc định với PostgreSQL; fingerprint ghi backend |
| Ingest | httpx, BeautifulSoup, pypdf layout extraction | Allowlist nguồn, redirect/DNS/size, parse/OCR quarantine, chunk điều/trang/parent, checksum/provenance |
| OCR ngoại tuyến | Tesseract vie+eng, pdftoppm; helper offline và PDF/image tooling | OCR sidecar phải đối chiếu; runtime Docker không chạy OCR phục vụ chat |
| Chuẩn bị vector | Checkpoint content/title/contract, notebook/worker Colab CPU | Giữ contract runtime/offline đồng nhất và vector nguyên trạng; không fine-tuning |
| Công cụ operator | Typer CLI và scripts candidate/audit/evaluation/package/restore/deploy | Operator usage riêng; output/attempt có phiên bản; DB khôi phục riêng và không drop |
| Phát hành | Docker Python slim, Render Free một worker, Cloudflare Pages/Wrangler, Supabase | Deploy ghim SHA, corpus Release/checksum, xác minh live và rollback; không tự thay hosting |
| Kiểm thử | pytest/pytest-asyncio/respx; Vitest; Playwright Chromium desktop/Pixel 7 | Fixture phần mềm khác model benchmark và khác browser production thật |
| CI/vận hành | GitHub Actions checks/deploy/evaluation/operations, secret scan, npm audit, memory check | Metadata cleanup/check theo lịch; không có SLA từ một lần kiểm tra; quality gate nội dung hiện là opt-in |
| Thiết kế/tài liệu | Figma team codex, Markdown/ADR, diagram-design revision ghim | Giữ nguồn UI thống nhất; sơ đồ HTML→helper SVG; không đổi sang Mermaid |

`cryptography` có trong dependency nhưng không được suy rằng backup hiện tại chứa hội thoại mã hóa: backup runtime chỉ corpus/config và cấm `include_sessions`. Bảng messages/traces/cache từng tồn tại trong migrations; migration 006 xóa payload và thu hồi quyền, runtime hiện không lưu nội dung.

## Contract ảnh hưởng trực tiếp đến v2

Request có một project công khai ring4, message tối đa 4.000 ký tự, history tối đa bốn cặp/12.000 ký tự. Ngân sách 6/12/2/1/90 và provider retry áp dụng toàn lượt. `prompt_context()` hiện chọn passage nguyên vẹn trong giới hạn dung lượng riêng cho Groq; không thể giả định tìm đủ nguồn đồng nghĩa mọi đoạn đều đã tới synthesis. Các thay đổi UI/phần trả lời phải thích ứng với nguồn thực sự được cung cấp và verify.

`Claim.kind` hiện là legal_rule/applicability/context. `Draft.next_steps` là chuỗi không có citation riêng; `ChatResult.content` do finish dựng từ claim đã qua cổng. Để thêm hành động/đầu mối có căn cứ cần sửa schema và policy tương ứng trong cùng pipeline, không chỉ thêm các heading bằng CSS.

`Document.source_kind` hiện chưa biểu diễn nguồn thủ tục hoặc danh bạ riêng. Nguồn thư viện reference-only không có chunks và không thể trở thành chứng cứ AI chỉ bằng việc UI mở được PDF. Source topics và alias giúp chọn/tìm, không chứng minh điều kiện pháp lý. Đây là lý do kế hoạch corpus tập trung coverage theo việc và vai trò nguồn thay vì chỉ tăng số tài liệu.

History client do người dùng kiểm soát, nên assistant text và citation cũ luôn phải kiểm tra lại. UI v2 không thể dùng lịch sử như hồ sơ hợp lệ hoặc dựa vào server để khôi phục đáp án sau mất SSE. Tính dễ dùng cần được thiết kế trong chính những ràng buộc này.
