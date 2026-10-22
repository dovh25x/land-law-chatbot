# Bounded Agentic RAG

`EXECUTION_MODE=agentic_rag` là mode production hiện tại; `BoundedAgenticRAG` nằm tại `backend/landlaw/agentic_rag.py`. `simple_rag` là rollback và mode `agentic` (LangGraph) chỉ còn legacy.

![Luồng quyết định Agentic RAG](diagrams/agent-flow.svg)

## Tool

Model chỉ thấy hai function đọc-only; ứng dụng validate tham số và thực thi:

| Tool | Tham số (validate server-side) | Kết quả |
|---|---|---|
| `search_legal_evidence` | `query` 1–600 ký tự, `topic` tùy chọn | Tối đa 5 đoạn reviewed kèm số hiệu, tiêu đề, locator, excerpt, applicability |
| `open_legal_provision` | `document_id` 1–120, `locator` 1–200, `query` tùy chọn | Đúng đoạn đã admitted của một điều/khoản, tối đa 3 chunk |

Không có SQL, ghi DB, filesystem, URL fetch, credential hay tool ngoài allow-list. Tool name lạ, JSON hỏng, document ngoài corpus và tham số quá dài bị từ chối mà không thực thi.

## Ngân sách thực thi

| Giới hạn | Giá trị |
|---|---|
| LLM request mỗi lượt | Tối đa 3; bình thường 1 (xã giao) hoặc 2 (pháp luật) |
| Tool execution | Tối đa 2, từ **một** tool decision duy nhất |
| Tool-decision thứ hai | Không |
| Repair loop | Không |
| Song song | Không (gpt-oss không hỗ trợ parallel tool calls) |
| Deadline | 90 giây/lượt |

## Tương thích provider Groq

- Tool decision: `tools` + `tool_choice="auto"`, không gửi `response_format` (Groq không hỗ trợ đồng thời strict Structured Outputs và tool use).
- Final generation: strict JSON schema `SimpleAnswer`, `tool_choice="none"`.
- `reasoning_effort="low"` cho cả hai leg; `medium` chỉ dùng cho schema legacy `Draft`/`Verification`.
- 429 → `limited` + `retry_after`; 400 tool/format → bỏ tool decision, fallback retrieval + generation, không retry vòng lặp.

## Định tuyến và hội thoại

- Model nhận history giới hạn (≤8 message, redact, 2000 ký tự/message) và tự chọn trả lời trực tiếp hay gọi tool.
- Xã giao/ngoài phạm vi: trả lời trực tiếp, không database, không citation.
- Câu pháp luật: nếu model trả lời trực tiếp mà không gọi tool, ứng dụng bắt buộc retrieval rồi generation; không phát hành đáp án pháp luật từ trí nhớ.
- Fallback `conversation.contextual_retrieval_query` mở rộng truy vấn cho tiếp nối rõ (`vậy`, `còn`, `thế`, `nhưng`, `đất tôi`, `nhà tôi`). Không suy diễn dữ kiện chưa có và không kế thừa chủ thể sau khi đổi đề tài.

## Nguồn và citation guard

- Mọi đoạn phải qua `Store.scoped_source_reviews` (receipt/checksum/policy v2) và `source_policy.applicability()` (`current`, `provision_specific`, `context`).
- `legal_text.validate_answer` kiểm tra theo từng câu/citation:
  - điều và khoản phải xuất hiện trong excerpt được dẫn;
  - số hiệu văn bản phải khớp `document_number` của nguồn được dẫn;
  - điều kiện thủ tục thêm vào (`phương án`, `phê duyệt`, `giấy chứng nhận`, `cư trú`, …) phải có trong nguồn;
  - nguồn `official_news`/`project_decision` không được chứng minh quyền lợi;
  - từ ngữ khẳng định tuyệt đối bị loại, nhưng câu phủ định an toàn ("chưa đủ chắc chắn") được giữ.
- Guard là bộ lọc từ chối, không phải bằng chứng đúng ngữ nghĩa hay thẩm định pháp lý độc lập.

## Thất bại và fallback

| Tình huống | Kết quả |
|---|---|
| Không có evidence admitted | `clarification_needed` hỏi đúng một dữ kiện (quyết định thu hồi, loại đất, giấy tờ) |
| Citation/reference không đạt | Clarification kèm tối đa 2 trích đoạn thật + review notice |
| 429 | `limited`, giữ `retry_after` |
| BudgetExceeded | Clarification trong ngân sách còn lại |
| Tool decision 400/5xx | Fallback retrieval + final generation |

## Khác biệt với legacy

| | `agentic_rag` (production) | `simple_rag` (rollback) | `agentic` (legacy) |
|---|---|---|---|
| Tool calling | Groq native, 2 tool đọc-only | Không | Planner JSON + tool nội bộ |
| LLM request/lượt | 1–2 (hard 3) | 1 | Tới 6 gồm retry/repair |
| Verification | Deterministic guard | Citation marker + guard | LLM verifier + cấu trúc nặng |
| Repair | Không | Không | 1 lần |

## Rollback

Đặt `EXECUTION_MODE=simple_rag` và redeploy SHA `625e90e84079950e953267d1e4caaf0cb3e8c8e5`. Corpus và policy v2 giữ nguyên; không cần restore database.
