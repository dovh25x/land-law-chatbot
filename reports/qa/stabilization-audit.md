# Stabilization audit — Hanoi Land Law Assistant

Date: 2026-10-22 (Asia/Ho_Chi_Minh) · Repository: `dovh25x/land-law-chatbot` · Scope: connection recovery (P0), follow-up retrieval (P1), time-boxed QA, release preparation.

## Baseline

| Item | Value |
| --- | --- |
| Branch at start | `main` @ `e9a4890` |
| Deployed frontend | Cloudflare Pages deployment `10378b38-a773-4b07-a6d3-839ac016babd`, commit `422d363` |
| Deployed backend | Render deploy `dep-dbcer729lscs739d2pkg`, commit `422d363` |
| Production bundle | contains `"Chưa xác minh được cấu hình hiện tại"`, does not contain the new degraded notice → P0 fix **not** in production |
| Preserved untracked work | `reports/simple-rag-pilot-*.json`, `.playwright-mcp/`, `e2e-evidence/` (untouched) |
| Work branch | `fix/connection-recovery` |

## P0 — recurring loss of connection (soft-lock)

**Root cause.** `frontend/src/App.tsx` had a single `generation` state that `refresh()` set to `null` before every check and only restored when `/readyz`, `/api/v1/status` **and** `/api/v1/documents` all succeeded. Automatic refresh was gated on `runtimeKnown` (`generation !== null`), so once a single background status or document request failed, `generation` stayed `null` and the retry effect disabled itself. `runtimeKnown` also drove the composer `disabled` state, therefore the only recovery was the manual "Kiểm tra kết nối" button. The long blocking banner was that same state.

**Fix** (commit `51fdb83`, merged to `main` as `2c61207`):

- `frontend/src/connection.ts` — framework-free `ConnectionController` with phases `connecting | healthy | degraded | unavailable | disabled`; last verified `GenerationStatus` + `verifiedAt` kept separate from reachability; single-flight status reads; monotonic sequence guard against stale responses; 2s→30s capped exponential backoff with ±20 % jitter; retries on `focus`, `visibilitychange` (only while visible) and `online`; timers cleared on unmount/hidden tab; server `retry_after` honoured for provider limits.
- `frontend/src/useConnection.ts` — `useSyncExternalStore` binding; controller created once per mount.
- `frontend/src/api.ts` — GET-only timeout (10s default) with classified errors: `offline`, `timeout`, `network`, `http_503`, `http_429`, `bad_response`. Chat POSTs still use raw `fetch` and are **never** replayed.
- `frontend/src/App.tsx` — documents and readiness decoupled from chat; `generation` is the last verified status, never cleared by a failed check; send button gated by verified capability (`canSubmit`), textarea stays editable so drafts survive; concise degraded notice; explicit disabled/source-only/provider-limited verdicts remain authoritative; a failed chat POST triggers one forced status re-check, not a resend.

**Reproduction/recovery evidence.**

- `frontend/src/connection.test.ts` — 12/12 (initial connect, one failure after healthy, consecutive failures with capped backoff, recovery timer, dedupe, focus/visibility/online, stop cleanup, explicit disabled, 429 `retry_after`, cached verdict separated from health, classification).
- `frontend/e2e/connection.spec.ts` — 6 scenarios × desktop/mobile = 12/12: transient status failure with concise notice + automatic recovery while answers/citations/draft survive; documents failure never disables chat; answer in progress survives a failed status check and one POST only; cold-start 503 recovers without the button; explicit provider-limited remains authoritative; expired session restores draft without replay.
- 10-minute soak: 60 fault cycles (24×503, 12×timeout, 12×network, 12×slow), 60/60 automatic recoveries (median 2.04s, max 2.75s), 48 degraded notices, 31 chats = 31 POSTs, max 4 status GETs per 10s, 0 composer locks, 0 draft losses, 0 duplicate submits, 0 page/console errors. Evidence: `reports/qa/soak-connection-2026-10-22.json`, `reports/qa/soak-final-desktop.png`.

## P1 — follow-up questions losing legal context

**Root cause.** `SimpleRAG.run()` embedded and searched only `request.message`. A follow-up such as "Vậy nếu nhà tôi chưa có sổ đỏ thì sao?" had no legal subject, so retrieval missed the compensation/taking chunks even though history was passed to generation.

**Fix** (commit `51fdb83`). Deterministic `_retrieval_query(message, history)` in `backend/landlaw/simple_rag.py`: only explicit Vietnamese follow-up openers (`vậy/thế/còn/trường hợp đó/…`) inherit the last user question (≤600 chars) for embedding + search; greetings/out-of-scope previous turns and unrelated topic switches do not inherit. Generation prompt, source gate, applicability and citation rules unchanged. No second LLM call.

**Tests.** +7 in `tests/test_simple_rag.py`: four follow-up forms inherit, unrelated topic switch does not, helper determinism, follow-up with no supporting corpus stays `insufficient_evidence` with zero model calls, inherited query still cites the reviewed passage (32/32 this file).

## P1 — status advertised expired reviewed passages

**Root cause.** `Store.source_gate_status()` evaluated each receipt scope at the scope's own `as_of_from`, so a daily window that had already ended still counted toward `eligible_passages`/`usable`. Chat already filters evidence to scopes valid at the request date (`SimpleRAG` + `scoped_source_reviews`), so `/api/v1/status` could advertise more coverage than the chat could use and stay "available" after a window lapsed.

**Evidence.** Production `/api/v1/status` (old build) reported `eligible_passages: 74`; querying the same policy/receipts at `local_date = 2026-10-22` returns **43** valid passages. `scripts`/tests use today-relative checks elsewhere (`test_scoped_source_gate`).

**Fix** (commit `9a23991`). `source_gate_status(release, as_of=None)` now evaluates at the requested date, defaulting to today in `Asia/Ho_Chi_Minh`; `eligible_passages`/`usable` match actual chat coverage and fail closed when today's coverage is empty. Checksum, receipt age (7 days), canonical receipt hash and scope-date rules unchanged.

**Tests.** New `test_gate_status_counts_only_passages_valid_today` (expired window → 0/False; historical `as_of` → 1/True); `tests/test_scoped_source_gate.py` 33/33; full backend 562 passed.

## Defect table

| ID | Severity | Component/file | User impact | Reproduction | Root cause | Evidence | Complexity | Status | Fix commit | Test verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0-01 | P0 | `frontend/src/App.tsx` (`refresh`, `runtimeKnown`), `api.ts` | Chat/composer permanently disabled after one transient status or documents failure; user must keep pressing "Kiểm tra kết nối" | Load page healthy, fail one `GET /api/v1/status` (503/timeout/network), let the retry window pass | `generation` cleared before each check, only restored if readyz+status+documents all succeed; auto-refresh gated on `runtimeKnown`; documents coupled to chat | old bundle contains blocking banner; new e2e reproduces failure and automatic recovery | moderate | **fixed** | `51fdb83` (`main` `2c61207`) | 12 unit + 12 e2e + 10-min soak 60/60 |
| P1-01 | P1 | `backend/landlaw/simple_rag.py` | Short follow-ups ("vậy nếu chưa có sổ đỏ?", "còn đất nông nghiệp?") often returned insufficient evidence | Ask Q1 about compensation, then a short follow-up | Retrieval embedded only the literal follow-up; no history context | +7 pytest cases; inherited query cites reviewed passage | quick | **fixed** | `51fdb83` | `tests/test_simple_rag.py` 32/32 |
| P1-02 | P1 | `backend/landlaw/store.py` (`source_gate_status`) | Status could advertise generation/clauses that had already expired (74 reported vs 43 valid today) | Compare `/api/v1/status.source_gate.eligible_passages` with today-valid receipt scopes | Scopes evaluated at `as_of_from` instead of the requested date | live status vs DB query; new test | quick | **fixed** | `9a23991` | 33/33 gate tests; 562 backend |
| P3-01 | P3 | `backend/landlaw/api.py` (`/api/v1/documents`) | In normal (non source-lookup) mode the response omits `as_of`; frontend tolerates it (date field only used in source-lookup mode, currently off) | `GET /api/v1/documents` → no `as_of` key | Response shape differs between modes | live probe | quick | deferred | — | — |
| P3-02 | P3 | `frontend/e2e/{redesign,navigation,figma,citizen,...}.spec.ts` | Test hygiene only; excluded from CI by `testIgnore` | Run with a config without `testIgnore` | Specs predate the citizen two-page UI (`Thư viện văn bản`, `.trace-link`, "Đánh giá hệ thống") | 11 passed / 15 failed on superseded selectors | moderate | deferred | — | active suite covers the behaviors |
| P3-03 | P3 | Cloudflare CSP | `connect-src` allows `http://localhost:8000` and `http://127.0.0.1:8000` in production | Inspect response CSP | Build-time API base includes local development origins | header probe | quick | deferred | — | — |
| P3-04 | P3 | Cloudflare headers | No `Strict-Transport-Security` header | Inspect response headers | Default Pages configuration | header probe | quick | deferred | — | — |
| P3-05 | P3 | `frontend/src/App.tsx` navigation | Browser Back leaves the SPA (`about:blank`); pages have no URLs | Answer, open library, press Back | In-memory page state, no router by design | UX script | large | deferred | — | state survives reload (history spec) |

### Suspected risks / decisions needed

- **`ALLOW_STALE_GENERATION=true` in Render.** It is only consulted when no scoped receipt gate exists (`api.py`), so today's scoped gate governs. It is still a latent global freshness bypass. Recommend setting it to `false` during the approved deploy, and keep it false. Requires approval because it changes deployment configuration.
- **Daily source-window rotation.** Today's policy has 43 valid passages; windows expire at 17:00 UTC (midnight Hanoi). After this fix, `/status` will honestly report `source_stale`/disable generation if the next window is not imported. Rotation remains an operational cadence decision; no code change made.
- **Corpus-wide freshness warning.** `/status` exposes `source_fresh:false` + `warning:"source_stale"` while the scoped gate is usable; the UI does not surface that warning because citations are restricted to fresh scopes. Informational, not currently misleading.

### Missing evidence / not tested

- Real Groq chat after the changes — not run; requires separately approved bounded budget (no credits spent).
- Manual Cloudflare Turnstile challenge — user-only by policy; production probe confirms the backend returns `challenge_required` without a token.
- Mobile virtual keyboard and real-device safe-area behaviour — not testable headless.
- Post-deployment production verification — pending explicit approval; CI success is not treated as deployment success.
- Database restore drill — no schema change; existing restore/gate tests only.

## QA sweep results

| Area | Result |
| --- | --- |
| Backend unit/integration | `pytest -q` → **562 passed** (includes API auth, 429 + `Retry-After`, session expiry, concurrency/semaphore, source gate, cancellation paths) |
| Frontend unit | `npm test` → **29 passed** (6 files) |
| Production build | `npm run build` → **success** (`tsc -b` + Vite) |
| Playwright (active suite) | **34 passed** desktop + mobile (connection 12, history 8, product 10, simple-rag 6) |
| Legacy UX specs | 11 passed; 15 failed only on pre-citizen labels/selectors; excluded by config, no behaviour regression found |
| UX probe | theme toggle + persistence; long answer; sticky composer; return-to-end; copy + live region; official link `target=_blank` + `rel=noopener noreferrer`; all pass (`reports/qa/ux-checks-2026-10-22.json`, `ux-long-answer-desktop.png`) |
| Secrets | `scripts/check_secrets.py` clean; production bundle has no `GROQ_API_KEY`, `INGRESS_SECRET`, `DATABASE_URL`, `IP_HASH_SECRET`, `TURNSTILE_SECRET`, `gsk_`, Postgres URL |
| Live API | `/healthz` 200; `/readyz` 200 (database ready, Postgres); `/api/v1/status` 200; `/api/v1/documents` 200 (60 documents + 11 references) |
| Auth/ingress | direct Render URL → **403 `untrusted_ingress`**; session create without Turnstile → **400 `challenge_required`**; chat without session → **422 `invalid_request`** |
| Security headers | CSP, `frame-ancestors 'none'`, `nosniff`, `no-referrer`, permissions policy present; HSTS absent (P3) |
| Timezone | backend `local_date()` uses `ZoneInfo("Asia/Ho_Chi_Minh")`; `/status.source_lookup_as_of = 2026-10-22` while UTC is still 2026-10-21 |
| Deployment config | `EXECUTION_MODE=simple_rag`, `GENERATION_ENABLED=true`, `SOURCE_LOOKUP_ONLY=false`, model/embedding contract matches; `ALLOW_STALE_GENERATION=true` flagged above |

## Release state

- Branch `fix/connection-recovery` → `51fdb83` (P0 + follow-up) and `9a23991` (availability reporting).
- PR #6 (`51fdb83`) checks passed and was **merged to `main` as `2c61207` at 18:34:56Z by the repository account**; this session did not issue a merge command and is reporting the fact rather than assuming CI deployed anything.
- PR #7 (`9a23991`) checks passed: `backend` 55s, `frontend` 1m10s, `image` 49s (run 39656475220).
- Production still serves `422d363` on both Pages and Render. No deployment has occurred.
- Deployment is a manual `workflow_dispatch` (`Deploy application`) pinned to `source_sha`; it re-runs backend/frontend checks, builds with production env, deploys Pages + Render, and verifies live navigation/source identity. Rollback anchors: Render `dep-dbcer729lscs739d2pkg` (`422d363`) and Pages deployment `10378b38…` (`422d363`).
- **Explicit approval required** before dispatching the workflow. After deployment, verify the production bundle no longer contains the old blocking banner, `/status` reports today-valid counts, and the manual Turnstile/chat path works.
