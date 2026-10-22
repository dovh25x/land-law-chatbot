# Tài liệu kỹ thuật

Tài liệu mô tả phạm vi, kiến trúc, API, vận hành và đánh giá của Hanoi Land Law Assistant. Kết quả đo và bằng chứng thuộc từng phiên bản nằm trong `reports/`; tài liệu thiết kế không thay thế bằng chứng thực thi. Runtime production hiện tại là **bounded Agentic RAG** (`EXECUTION_MODE=agentic_rag`); `simple_rag` là rollback, `agentic` (LangGraph) là legacy.

## Lộ trình đọc

### Bắt đầu

| Nhu cầu | Tài liệu |
|---|---|
| Cài đặt, chạy thử, cấu trúc repository | [README gốc](../README.md) |
| Hiểu vấn đề, người dùng, phạm vi MVP | [PRD](PRD.md) |
| Đọc thiết kế đích cho người dân | [Thiết kế lại v2](redesign/README.md) · [trạng thái triển khai](redesign/IMPLEMENTATION.md) (design record, có phần đã lỗi thời) |

### Kiến trúc và Agentic RAG

| Nhu cầu | Tài liệu |
|---|---|
| Kiến trúc triển khai, thành phần, bảo mật, giới hạn | [Kiến trúc](ARCHITECTURE.md) |
| Tool calling, budget, citation/reference guard, rollback | [Agentic RAG](AGENTIC_RAG.md) |
| Phân tích pipeline legacy plan/repair/verify (không còn là production) | [Agent flow — legacy](AGENT_FLOW.md) |
| Quyết định kiến trúc | [ADR](adr/README.md) |

### Giao diện, API và dữ liệu

| Nhu cầu | Tài liệu |
|---|---|
| Tích hợp phiên, chat SSE, schema request/response | [API](API.md) |
| UI, panel nguồn, history, responsive, accessibility | [Frontend](FRONTEND.md) |
| Nguồn pháp luật, corpus release, receipt và policy | [Kiến trúc § nguồn](ARCHITECTURE.md#nguồn-pháp-luật-và-source-gate) · [Vận hành § source review](OPERATIONS.md#source-review-và-standing-snapshot) |

### Đánh giá và vận hành

| Nhu cầu | Tài liệu |
|---|---|
| Phương pháp đánh giá, artifact hiện hành | [Đánh giá](EVALUATION.md) |
| Kết quả release Agentic RAG (release cũ, giữ lịch sử) | [FINAL_RESULT](../reports/evaluation/agentic-rag-final/FINAL_RESULT.md) · [metrics](../reports/evaluation/agentic-rag-final/metrics.json) |
| Hotfix legal-answer (tất định, chưa deploy) | [Report](../reports/evaluation/agentic-rag-legal-answer-hotfix/README.md) |
| Pilot Groq hậu hotfix (PARTIAL, chưa đủ release gate) | [Report và review](../reports/evaluation/agentic-rag-post-hotfix-pilot/README.md) |
| Triển khai, backup, rollback, sự cố | [Vận hành](OPERATIONS.md) |
| Sơ đồ và quy trình diagram-design | [Diagrams](diagrams/README.md) |

### Lịch sử / archive

Các tài liệu sau là bản ghi lịch sử, không mô tả runtime hiện tại: `docs/redesign/SYSTEM.md`, `docs/redesign/ROADMAP.md`, `docs/redesign/EVALUATION.md`, `docs/AGENT_FLOW.md`, các report `reports/production-*-20261020/`, `reports/evaluation/ring4-c4f0c661/`, `reports/deployment-ring4.json`. Khi mâu thuẫn với tài liệu đang hoạt động, tài liệu kiến trúc/Agentic RAG hiện hành là nguồn đúng.

## Quy ước tài liệu

- README là điểm bắt đầu; mỗi tài liệu chuyên đề chịu trách nhiệm một chủ đề và dùng liên kết thay vì sao chép.
- Phân biệt rõ deterministic tests, offline evaluation và real-model measurements; không trộn cohort cũ với kết quả mới.
- `reports/` giữ nguyên artifact lịch sử; không sửa số liệu cũ để khớp cấu hình mới.
- `.env.example` chỉ liệt kê tên biến; secret quản lý ngoài Git.
