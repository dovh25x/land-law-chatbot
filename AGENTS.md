# Ngữ cảnh phát triển

Hanoi Land Law Assistant chỉ phục vụ Vành đai 4 tại Hà Nội: tra cứu bồi thường, hỗ trợ và tái định cư từ nguồn có xuất xứ. Không xác định thửa đất, tính tiền hoặc bảo đảm quyền lợi cá nhân.

## Ràng buộc kiến trúc

- Giữ một pipeline FastAPI + bounded Agentic RAG production (Groq GPT-OSS 120B, native tool calling) và E5 ONNX Q8 384 chiều, contract `multilingual-e5-small-onnx-q8-window-v1`. `simple_rag` là rollback; LangGraph `agentic` là legacy. Không tự đổi model, embedding hoặc hosting Free.
- React/Vite → Cloudflare signed ingress → Render → PostgreSQL/pgvector. SQLite dành cho local; kết quả hai backend không tự tương đương.
- History, citation và trace chỉ lưu IndexedDB trong 7 ngày. Server chỉ giữ metadata; không lưu messages, answer cache hoặc trace chi tiết. History do client gửi không phải chứng cứ.
- Quota ứng dụng chỉ áp dụng cho public; trusted operator CLI ghi usage riêng. Cả hai tuân thủ giới hạn thực tế của Groq.
- Mỗi lượt `agentic_rag` tối đa 3 LLM request (bình thường 1–2), 2 tool execution, không repair loop và deadline 90 giây. Không phát đáp án pháp luật không qua evidence hoặc tự nối điều kiện để vượt citation/reference guard.
- Claim phải độc lập, đúng nguồn, chủ thể, điều kiện, ngoại lệ, hệ quả và thời điểm. Loại cả phần phụ thuộc bị mất ngữ cảnh.
- Chỉ vận hành nguồn Vành đai 4 và luật chung liên quan. Không embedding lại khi chỉ lọc corpus; không thêm pipeline, reranker, fine-tuning, multi-agent, GIS hoặc tính năng ngoài phạm vi.

## Nguồn ngữ cảnh

[README](README.md) dành cho cài đặt và đọc source. [docs](docs/README.md) chứa PRD, kiến trúc, API, frontend, vận hành, đánh giá và ADR. `reports/` chứa bằng chứng có phiên bản; không sửa artifact lịch sử để giả khớp cấu hình.

`backend/landlaw/` chứa runtime; `frontend/` chứa UI và ingress; `data/` chứa manifest/evaluation; `migrations/` chứa schema PostgreSQL; `scripts/` chứa tác vụ vận hành.

UI theo Figma team `codex` và [handoff](docs/FRONTEND.md). Ưu tiên Code agent; người dùng đã cho phép thiết kế trực tiếp trong Figma khi công cụ gửi prompt không hoạt động. Không tự thay hướng thiết kế ngoài nguồn đã thống nhất.

Mọi diagram hệ thống phải dùng [diagram-design](https://github.com/cathrynlavery/diagram-design) theo [quy trình và revision đã ghim](docs/diagrams/README.md). Giữ source HTML, xuất SVG bằng helper và nhúng vào Markdown; không thay bằng Mermaid hoặc công cụ khác.

## Quy tắc thay đổi và kiểm tra

Ưu tiên patch có regression tái hiện được, không refactor toàn bộ agent. Không log secret hoặc nội dung hội thoại. Không drop database; restore vào database riêng. Chỉ gỡ Release cũ sau khi bản mới phát hành và restore đạt. Rollback không phục hồi server history hoặc corpus đa dự án.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Giữ nguyên bộ 20+4 đã khóa; natural suite khóa trước prompt edits. Model evaluation chỉ chạy lại khi lỗi hoặc thay đổi liên quan; giữ mọi attempt, review gắn checksum, không chọn kết quả đẹp. Fixture pass, citation integrity và faithfulness không thay thế thẩm định pháp lý.

Deploy ghim SHA đã kiểm thử và xác minh corpus/fingerprint. Ghi rõ phần chưa kiểm tra; không tuyên bố passed khi chưa xác minh. Tài liệu chỉ mô tả sản phẩm và quy trình kỹ thuật, không sao chép số liệu dễ hết hạn từ báo cáo.
