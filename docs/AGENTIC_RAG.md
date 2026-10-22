# Bounded Agentic RAG

`EXECUTION_MODE=agentic_rag` là mode production hiện tại; `BoundedAgenticRAG` nằm tại `backend/landlaw/agentic_rag.py`. `simple_rag` là rollback và mode `agentic` (LangGraph) chỉ còn legacy.

> **Đã phát hành PR #13:** production chạy SHA `1a9718f03ed261f3511598488ab273b6bf5e0b92`, gồm claim-aware validation, marker nhóm, fallback ngắn và direct-first ordering. [Receipt release và kiểm tra public](../reports/releases/academic-mvp-1a9718f/README.md) tách biệt với pilot Groq PARTIAL; đây là MVP học thuật, không phải dịch vụ đã thẩm định pháp lý.

![Luồng quyết định Agentic RAG](diagrams/agent-flow.svg)

## Tool

Model chỉ thấy hai function đọc-only; ứng dụng validate tham số và thực thi:

| Tool | Tham số (validate server-side) | Kết quả |
|---|---|---|
| `search_legal_evidence` | `query` 1–600 ký tự, `topic` tùy chọn | Tối đa 5 đoạn reviewed kèm số hiệu, tiêu đề, locator, excerpt, applicability; ưu tiên nguồn trực tiếp và locator khác nhau |
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

## Chọn và xếp evidence

- `search_legal_evidence` trả tối đa 5 đoạn đã qua source gate và applicability.
- Với câu hỏi pháp lý, đoạn `legal` được xếp trước `official_news`/`project_decision`; nếu có ít nhất một đoạn legal, tối đa một đoạn context được giữ.
- Trong nhóm legal, văn bản trực tiếp về bồi thường/hỗ trợ/tái định cư/Luật Đất đai được xếp trước nghị quyết có tiêu đề tháo gỡ/vướng mắc/chuyển tiếp. Đây là quy tắc thứ tự tất định, không phải reranker ngữ nghĩa. Nếu chính câu hỏi nói về cơ chế chuyển tiếp hoặc Nghị quyết 254/2025, thứ tự search được giữ nguyên.
- Search ưu tiên locator khác nhau trước khi dùng lại chunk trùng điều; chunk trùng chỉ còn là fallback. `open_legal_provision` không áp dụng bước đa dạng hóa này vì người dùng chủ động mở đúng một điều.
- Tối đa một tin/dự án context không được dùng để chứng minh quyền lợi hộ dân.

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
- `legal_text.validate_answer_result` kiểm tra theo từng câu/citation:
  - **câu khẳng định** quy tắc, điều kiện, quyền, nghĩa vụ hoặc hệ quả pháp lý phải có marker trong chính câu đó; câu hỏi làm rõ, câu dẫn nhập và câu nêu giới hạn không cần marker;
  - marker nhóm `[S1, S2]`, `[S1; S2]` và dạng full-width `【S1】【S2】` được chuẩn hóa; ID không có trong source map bị từ chối;
  - điều và khoản phải xuất hiện trong excerpt được dẫn;
  - số hiệu văn bản phải khớp `document_number` của nguồn được dẫn;
  - điều kiện thủ tục thêm vào (`phương án`, `phê duyệt`, `giấy chứng nhận`, `cư trú`, …) phải có trong nguồn;
  - nguồn `official_news`/`project_decision` không được chứng minh quyền lợi;
  - từ ngữ khẳng định tuyệt đối bị loại, nhưng câu phủ định an toàn ("chưa đủ chắc chắn") và câu hỏi "có được hưởng … không?" được giữ.
- `limitation` chỉ được chứa câu nêu giới hạn; nếu chuyển một claim pháp lý vào đó, draft bị từ chối.
- Kết quả validation có reason code nội bộ như `missing_required_citation`, `unknown_citation_id`, `reference_identity_mismatch`, `unsupported_legal_condition`, `invalid_claim_grounding`, `unsupported_legal_claim`, `grounded_answer`, `legitimate_clarification`. Trace chỉ ghi reason code đã rút gọn, số marker/claim và document ID; không ghi draft, excerpt hay nội dung hội thoại. UI công khai không render trace/validator internals.
- Guard là bộ lọc từ chối, không phải bằng chứng đúng ngữ nghĩa hay thẩm định pháp lý độc lập. Nó không chứng minh một paraphrase không nêu điều/khoản cụ thể là đúng nguồn.

## Thất bại và fallback

| Tình huống | Kết quả |
|---|---|
| Không có evidence admitted | `clarification_needed` hỏi đúng một dữ kiện (quyết định thu hồi, loại đất, giấy tờ) |
| Draft chỉ có câu hỏi làm rõ, không marker | `clarification_needed`, giữ nguyên câu hỏi, không gọi đó là task success |
| Citation/reference không đạt | Fallback ngắn: tối đa 2 danh tính nguồn (số hiệu + locator), một câu hỏi làm rõ, review notice nếu có; **không** đổ trích đoạn nguyên văn |
| 429 | `limited`, giữ `retry_after` |
| BudgetExceeded | Clarification ngắn trong ngân sách còn lại |
| Tool decision 400/5xx | Fallback retrieval + final generation |

Fallback không thay thế đáp án pháp lý và không tạo entitlement. Citation rỗng là hợp lệ khi chỉ có câu hỏi làm rõ; `support_level=insufficient` phản ánh đúng giới hạn đó.

## Khác biệt với legacy

| | `agentic_rag` (production) | `simple_rag` (rollback) | `agentic` (legacy) |
|---|---|---|---|
| Tool calling | Groq native, 2 tool đọc-only | Không | Planner JSON + tool nội bộ |
| LLM request/lượt | 1–2 (hard 3) | 1 | Tới 6 gồm retry/repair |
| Verification | Deterministic guard | Citation marker + guard | LLM verifier + cấu trúc nặng |
| Repair | Không | Không | 1 lần |

## Rollback

Rollback ứng dụng gần nhất bằng workflow triển khai SHA `b1c10f4bad6b89f1d555eb08f5216b4b285be6d6` lên cả Pages/Render, giữ `EXECUTION_MODE=agentic_rag` và nguyên corpus/policy. Chỉ khi chủ động chọn rollback mode legacy mới đặt `EXECUTION_MODE=simple_rag` và redeploy SHA `625e90e84079950e953267d1e4caaf0cb3e8c8e5`; không cần restore database.

Hotfix claim-aware chỉ áp dụng cho `agentic_rag`. `simple_rag` vẫn dùng guard citation toàn cục và fallback cũ; rollback không tự mang theo sửa đổi này. Vì vậy chỉ rollback khi chấp nhận hành vi cũ, không dùng `simple_rag` làm bằng chứng cho hiệu quả hotfix.
