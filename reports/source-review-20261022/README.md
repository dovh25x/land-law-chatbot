# Daily source-gate rotation 2026-10-22

Mechanical re-verification and window rotation that unblocked the public chat
after the pinned receipt windows (`2026-10-21 → 2026-10-22`) expired at
midnight Hanoi. Executed after explicit user authorization for the
"mechanical re-verify + rotate" path.

## What happened

- Prod gate `source_gate:corpus-1afca764aa6692e0` pinned receipts whose only
  current-day scopes ended at `2026-10-22` (exclusive). After midnight
  (Asia/Ho_Chi_Minh) `as_of=2026-10-22` failed the scope check
  (`as_of_from <= as_of < as_of_to`, `store.scoped_source_reviews`) for every
  pinned passage → all citizen questions returned `insufficient_evidence`.
- Measured via read-only production queries; reproduced first in an offline
  replay (`replay-validation.json`, `before_rotation_2026_10_22`).

## What this directory contains

1. `recheck_sources.py` + `recheck-access.json` — re-fetch of every official
   source artifact pinned by the gate (10 documents; 27 byte-hashed PDFs/images
   + 1 HTML page verified by extracted-text equality against the Oct-20 snapshot).
   **Result: 28/28 unchanged** — every checksum matched the pinned release, so
   the human legal review of 2026-10-20/21 stays attached to identical content.
2. `build_rotation.py` + `receipts-20261022/` + `source-gate-20261022.json`
   — append-only rotation: new scope window `2026-10-22 → 2026-10-23` with the
   identical immutable chunk checksums for the 7 receipts that had a
   current-day scope; the 3 historical-only receipts (`luat-43-2024`,
   `nd-151-2025`, `qd-10-2026-hanoi`) are byte-identical copies and were not
   hash-changed. `checked_at` refreshed to the re-check time; re-fetch evidence
   appended to `review_evidence`; a mechanical-recheck note appended to
   `relation_review`. No historical window or reviewed text was altered.
3. `replay_validation.py` + `replay-validation.json` — isolated SQLite replay:
   blocker reproduced before rotation, then gate usable and all pinned chunks
   fresh at `as_of=2026-10-22`, pilot chunks fresh, historical windows and the
   previous window still resolving.
4. `apply_production.py` + `apply-production.json` — owner-role application to
   the production database: additive receipt inserts + gate pointer update
   only; documents unchanged; zero LLM calls.

## Production result

- Gate policy SHA256: `015e33634ae920889271bbfcdf1a3e20977116b21c6c10be4face0c962d8d220`
- `/api/v1/status` after rotation: `source_gate.usable=true`, 74 eligible passages.
- Public chat E2E with a human solving the Cloudflare Turnstile challenge is the
  remaining manual step.

## Known expiry

- Windows expire again at midnight Hanoi (17:00 UTC) on 2026-10-22. A durable
  daily cadence decision (manual/automated rotation, or a deliberate window
  policy change) is still pending with the operator.
