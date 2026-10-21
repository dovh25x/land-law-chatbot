# UI metadata race — confirmed and fixed locally

Public source-only browser run02 **FAIL** exposed a real presentation defect, not a legal-model failure or a timeout harness issue. The failure artifact and screenshots are preserved.

[Public timing diagnosis](history-race-2026-10-21T10-37-55-451Z/report.json) on the deployed pre-patch UI showed:

- At 528 ms after reload, saved local history already displayed an old citation button and enabled input; current runtime metadata had not arrived.
- At 871 ms, clicking that saved citation exposed an explicitly synthetic, unreviewed excerpt in the source panel.
- At 20.767 seconds, source-only metadata arrived; the unverified-history label appeared, citations/panel disappeared, and input became disabled.

This used synthetic data only in an isolated browser context. No session/chat/model requests or server source-guard bypass occurred. The UI nevertheless presented untrusted saved content as a source before knowing the current mode, which is a release safety defect.

## Minimal presentation fix

Only `frontend/src/App.tsx` and focused source-lookup Playwright tests changed:

1. Separate `runtimeKnown` from source-only mode. During startup, refresh or metadata failure, show saved assistant text with an unverified-history label; suppress structured CitizenAnswer, citations, actions, trace and client-excerpt source panels.
2. Enable input/send/Turnstile only after confirmed normal-mode generation availability. `send()` independently checks the same condition.
3. Clear stale generation status at full refresh start. Restore trusted status only when readiness is ready and status/source metadata reads completed successfully. Failed configuration keeps the existing warning and refresh button visible, including when `/readyz` itself succeeded.
4. A focus/visibility status-only request cannot revive unknown configuration. Background failure returns to unknown; recovery uses the existing complete refresh.

No server/model/prompt/verifier/corpus/embedding changes; browser history retained. Known normal mode still works after valid metadata or explicit recovery. Backend runtime fingerprint remains `8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464`; presentation fingerprint changes to `bfcf2f0e284b8b158e5941039369d81fb20561827273957de43584d0822200bd`.

## Local checks at final patch freeze

| Check | Result | Evidence |
|---|---|---|
| Frontend unit | 16 PASS | [unit log](frontend-unknown-runtime-unit-final.log) |
| TypeScript/Vite build | PASS | [build log](frontend-unknown-runtime-build-final.log) |
| Focused source lookup + normal product behavior | 16 Playwright PASS, 50.1 seconds | [browser log](frontend-unknown-runtime-playwright-final.log) |
| Whitespace | PASS | `git diff --check` |

New regressions cover delayed metadata while history loads, failed metadata after previously known normal availability, no citation/structured answer/Turnstile while unknown, focus-status recovery veto, and successful explicit full refresh. Desktop and mobile fixtures pass. These are software fixtures, not a replacement for public retesting after deployment.

Pre-patch public run01 remains a separate test-harness URL expectation failure; run02 is the actual UI safety failure. Neither is deleted or relabeled PASS. Release owner must commit/redeploy the UI patch and the real public browser must verify the initial history window is closed. No further model run is authorized or needed for this presentation fix.
