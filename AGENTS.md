# Project context

Hanoi Land Law Assistant phục vụ duy nhất Vành đai 4 tại Hà Nội: tra cứu bồi thường, hỗ trợ, tái định cư từ nguồn có xuất xứ. Không xác định thửa đất, tính tiền hoặc bảo đảm quyền lợi cá nhân.

## Decisions

- Một pipeline FastAPI/LangGraph/Groq GPT-OSS 120B; E5 ONNX Q8 384 chiều, contract `multilingual-e5-small-onnx-q8-window-v1`. Không đổi model/embedding/hosting Free ngoài yêu cầu.
- Frontend React/Vite → Cloudflare signed ingress → Render → PostgreSQL/pgvector. SQLite dành cho local.
- History, citations, trace chỉ lưu IndexedDB 7 ngày. Server chỉ xử lý nội dung trong request; không lưu messages, answer cache hoặc trace chi tiết. History từ client không phải chứng cứ.
- Public usage có quota; operator CLI/dev không chịu quota ứng dụng. Mỗi lượt vẫn giữ 6 LLM calls, 12 tools, 2 retrieval rounds, 1 repair, 90 giây.
- Không phát đáp án trước verify; không tự nối điều kiện để vượt kiểm chứng. Mệnh đề phải độc lập và gắn đúng nguồn/chủ thể/điều kiện.
- Thiết kế UI trong Figma team `codex`, triển khai theo handoff tại `docs/FRONTEND.md`. Ưu tiên Code agent; người dùng đã cho phép thiết kế trực tiếp trên Figma khi công cụ gửi prompt không hoạt động.
- Giữ nguyên 20+4 câu đã khóa. Natural suite khóa trước prompt edits. Review gắn checksum, giữ mọi attempt; fixture tests không chứng minh chất lượng model.
- Chỉ corpus Vành đai 4 và luật chung liên quan được vận hành/phát hành. Không embedding lại khi chỉ lọc corpus.

## Navigation

`backend/landlaw/` API/agent/provider/store; `frontend/` giao diện; `data/` manifest/evaluation; `migrations/` PostgreSQL; `scripts/` vận hành; `reports/` bằng chứng có phiên bản; `docs/` PRD, architecture, API, operations, evaluation, ADR và frontend handoff. README dành cho quickstart và đọc source. Tài liệu chỉ mô tả sản phẩm và quy trình kỹ thuật.

## Work safely

Ưu tiên thay đổi có regression tái hiện được; không refactor toàn bộ agent hoặc thêm pipeline/tính năng ngoài phạm vi. Không log secret/nội dung hội thoại. Không drop database. Restore vào database riêng. Chỉ gỡ Release cũ sau khi corpus mới phát hành và restore đạt. Rollback không phục hồi server history hoặc corpus nhiều dự án.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_secrets.py
cd frontend
npm test
npm run build
npm run test:e2e
```

Model evaluation chỉ chạy lại khi lỗi/thay đổi liên quan, không chọn kết quả đẹp. Không đánh đồng citation integrity với faithfulness hoặc thẩm định pháp lý. Deploy ghim SHA và kiểm tra corpus/fingerprint, không tuyên bố passed nếu chưa xác minh.
