# Nguồn và quy trình diagram-design

Các sơ đồ kỹ thuật dùng [diagram-design](https://github.com/cathrynlavery/diagram-design) (MIT) ghim commit upstream:

`550fd66edff058bc73056c3416b76d69cfe865ba`

Skill được cài ngoài repository tại `~/.config/opencode/skills/diagram-design` (symlink tới `~/tools/diagram-design/skills/diagram-design`), không copy upstream vào project. Style của project lấy từ `frontend/src/styles.css` và lưu trong profile `~/.diagram-design/profiles/land-law.md` + marker `.diagram-design`:

- paper `#ffffff`, tint `#f7f7f8`, ink `#202123`, muted `#62666d`, border `#dadde1`, accent `#805400`
- font system (không phụ thuộc Google Fonts khi render SVG)
- export bằng `skills/diagram-design/scripts/export_svg.py --system-fonts`

## Danh mục

| Sơ đồ | Loại | Nguồn HTML | SVG nhúng | Markdown sử dụng | Trạng thái |
|---|---|---|---|---|---|
| Kiến trúc triển khai | Architecture | [architecture.html](architecture.html) | [architecture.svg](architecture.svg) | `README.md`, `docs/ARCHITECTURE.md` | Đã cập nhật claim-aware guard |
| Luồng quyết định Agentic RAG | Flowchart | [agent-flow.html](agent-flow.html) | [agent-flow.svg](agent-flow.svg) | `docs/ARCHITECTURE.md`, `docs/AGENTIC_RAG.md` | Đã cập nhật fallback ngắn và evidence ordering |
| Trình tự chat | Sequence | [chat-sequence.html](chat-sequence.html) | [chat-sequence.svg](chat-sequence.svg) | `docs/ARCHITECTURE.md` | Đã cập nhật |
| Retrieval và admission | Data flow | [retrieval-admission.html](retrieval-admission.html) | [retrieval-admission.svg](retrieval-admission.svg) | `README.md`, `docs/ARCHITECTURE.md` | Đã cập nhật claim-aware guard và direct-first |
| Triển khai và phục hồi | Deployment | [deploy-recovery.html](deploy-recovery.html) | [deploy-recovery.svg](deploy-recovery.svg) | `docs/OPERATIONS.md` | Đã cập nhật |
| Vòng đời corpus | Process | [corpus-lifecycle.html](corpus-lifecycle.html) | [corpus-lifecycle.svg](corpus-lifecycle.svg) | `docs/redesign/CORPUS.md` | Giữ và recolor |
| Cổng phát hành (legacy) | Flowchart | [agent-publication-gate.html](agent-publication-gate.html) | [agent-publication-gate.svg](agent-publication-gate.svg) | `docs/AGENT_FLOW.md` | Legacy LangGraph, không phải production |

## Xác minh

Mỗi file HTML đã qua:

```bash
python3 ~/tools/diagram-design/skills/diagram-design/scripts/self_check.py --offline <file>.html
python3 ~/tools/diagram-design/scripts/verify-geometry.py <file>.html
```

Kết quả 22/10/2026 (sau hotfix legal-answer): 6/6 sơ đồ hiện hành pass self-check và geometry (0 finding); ba sơ đồ thay đổi semantics (`agent-flow`, `architecture`, `retrieval-admission`) đã export lại SVG và xem trực quan. `agent-publication-gate` giữ nguyên như tài liệu legacy, gồm cả tham chiếu font cũ. SVG hiện hành không chứa JavaScript, không gọi Google Fonts và render trực tiếp trong GitHub Markdown.

## Quy trình cập nhật

1. Sửa file HTML tương ứng (source duy nhất của sơ đồ).
2. Đối chiếu nội dung với source code thật: `backend/landlaw/agentic_rag.py`, `provider.py`, `store.py`, `api.py`, `frontend/functions/api/[[path]].ts`, `.github/workflows/`.
3. Export lại SVG bằng helper `--system-fonts`.
4. Chạy self-check + verify-geometry + xem trực quan PNG trước khi commit.
5. Commit cả HTML và SVG; không sửa riêng SVG để lệch HTML.
