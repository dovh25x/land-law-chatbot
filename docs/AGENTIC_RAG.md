# Bounded Agentic RAG

`EXECUTION_MODE=agentic_rag` selects `BoundedAgenticRAG`
(`backend/landlaw/agentic_rag.py`). The previous `simple_rag` path remains as the
rollback mode until production activation is approved.

## Tools

The model sees exactly two read-only function definitions:

| Tool | Arguments (validated server-side) | Result |
|---|---|---|
| `search_legal_evidence` | `query` (1–600 chars), optional `topic` enum | Up to five reviewed passages with document number, title, locator, excerpt and applicability |
| `open_legal_provision` | `document_id` (1–120), `locator` (1–200), optional `query` | Exact admissible chunks of one article/provision, bounded to three chunks |

No SQL, filesystem, URL fetch, write or credential capability is exposed.
Unknown tool names, malformed JSON, unknown document IDs and overlong
arguments are rejected without execution.

## Request and tool budget

- At most **3 Groq requests per turn** as a hard guard, and at most **2** in the
  normal path: one tool-decision request plus one final structured generation.
- At most **2 application-controlled tool executions** returned by that single
  decision. There is no second tool-decision round trip; gpt-oss does not
  support parallel tool calls, so this is normally one execution.
- No parallel tool execution, no automatic repair loop, no unbounded reasoning.
- Social turns finish in request 1 with a natural model reply and no retrieval.
- Legal questions are forced through reviewed evidence even when the model returns
  a direct answer: the application then performs one bounded retrieval and final generation.

Groq does not support strict Structured Outputs together with tool use, so the
tool-decision request sends `tools` + `tool_choice="auto"` without
`response_format`; the final answer is a separate strict-schema request.

## Routing and conversation

- The model receives the bounded client history (last 8 messages, redacted, 2000 chars each)
  plus the current question. It decides whether a tool is needed based on subject,
  history and scope.
- `conversation.contextual_retrieval_query` is a deterministic fallback for explicit
  follow-ups (`vậy`, `còn`, `thế`, `nhưng`, `đất tôi`, `nhà tôi`, ...) when the model
  does not rewrite the query itself.
- Out-of-scope requests are declined in the model's direct reply; the deterministic
  classifier is used only as a subject guard, not as a template answer.
- No user facts are inferred from the project name, a planning map or an assistant
  answer in history.

## Evidence and citation validation

- Every passage is re-checked with `Store.scoped_source_reviews` and
  `source_policy.applicability`; only `fresh`, `standing` or `reviewed_window`
  evidence with `current`, `provision_specific` or `context` applicability is used.
- `legal_text.validate_answer` checks per citation segment:
  - article and paragraph identifiers must appear in the cited excerpt;
  - document numbers must match the cited document, not merely be mentioned somewhere;
  - specific added conditions (`phương án`, `phê duyệt`, `giấy chứng nhận`, `cư trú`, ...)
    must appear in the cited evidence;
  - absolute certainty wording is rejected, while negated certainty
    (“chưa đủ chắc chắn”) is allowed.
- Invalid drafts fall back to a bounded excerpt clarification, never to an
  unsupported legal conclusion. The guard is a rejection filter, not proof of
  legal correctness or an independent legal review.

## Error behavior

- `RateLimited` → `status="limited"` with provider `retry_after`.
- `ProviderUnavailable` → `status="error"` without inventing an answer.
- `BudgetExceeded` or exhausted turn budget → bounded clarification based on the
  retrieved excerpts.
- No evidence after tools and fallback retrieval → one targeted clarification
  that names the actual coverage gap.

## Rollback

Set `EXECUTION_MODE=simple_rag` and redeploy the last tested runtime. The corpus
and source policy are unchanged by this mode switch.
