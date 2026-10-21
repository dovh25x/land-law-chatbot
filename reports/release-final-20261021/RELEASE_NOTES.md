# Hanoi Land Law Assistant — academic verified-source MVP

Public demo: [hanoi-land-law.pages.dev](https://hanoi-land-law.pages.dev).

This release serves **verified legal excerpts only**. Generative chat is disabled. It does not determine a household's entitlement, calculate compensation, identify land parcels, or provide a validated generated legal answer.

## Provenance and checks

- Deployed/tested application commit: `ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec`.
- [Exact-code CI](https://github.com/dovh25x/land-law-chatbot/actions/runs/39588182288): 529 backend tests on Python 3.12; 16 frontend tests; build and audit; 110 Playwright tests; Docker checks. Local full browser suite also passed 110 tests.
- Runtime PostgreSQL fingerprint: `8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464`.
- Corpus: `corpus-1afca764aa6692e0`; payload SHA256 `7ce7956ae35c7006b5bfd7d10d516fa9e8e47fe2f073e471ceecbb34b412d317`.
- Actual public desktop/mobile-emulation source lookup passed: date filters, exact excerpt checksums, official QĐ40 page navigation, immediate unverified-history label, reload and local-history deletion. No model/session requests were made by these checks.
- Human Turnstile, generated answers, generative follow-up and physical-device testing are not established by this release.

The Git tag includes final documentation and evidence. Application bytes remain pinned to the deployed/tested commit above; the publication receipt records the exact tag target separately.

## Legal and experimental limits

There are 43 admitted excerpts from seven documents for **21 October 2026**, and 25 reviewed historical excerpts for 2 August 2024. For 22/23 October only one QĐ40 header is in scope; it is not business-law coverage. Select 21 October explicitly as a historical review date when demonstrating later. A receipt is not evergreen: renew substantive review before expiry or unsupported dates; never edit timestamps or bypass the source gate.

The archive contains 60 documents / 7,396 chunks for reproducibility; this does **not** mean the whole archive is verified for current-law conclusions. The source-only API denies unreviewed excerpts. Restore does not import reviews implicitly: use the checksum-bound receipt bundle, subject to current review-validation rules.

Historical retrieval Recall@5 was macro **97.37% over 19 queries**, micro **95.24% (20/21 gold labels)** on SQLite under a different recorded fingerprint. This is not legal-answer accuracy or PostgreSQL retrieval validation. S06 remains FAIL; Phase3A C01 remains INCOMPLETE and C02/C03 NOT RUN. The one independently authorized new C02 attempt is INCOMPLETE after one HTTP400 JSON failure and conservative budget stop. No additional model or judge call followed. Current semantic citation accuracy, answer correctness, RAGAS and false-abstention metrics are not established.

## Downloads

- Vietnamese final report PDF, editable 12-slide PPTX and companion slide PDF.
- Academic submission ZIP with documentation, provenance and selected metadata; overlay it on the source archive for complete relative evidence links.
- `corpus-backup.json` and `corpus-manifest.json`: corpus-only reproducibility asset; no sessions, messages, trace history or credentials.
- `legal-source-receipts.zip`: 11 scoped receipts plus pinned policy; the full review provenance is in the source archive.
- `release-manifest.json`, `EVIDENCE_INDEX.md`, `SHA256SUMS`.

Verify SHA256 before use. Read the source archive's `reports/submission-20261021/README.md`, `DEMO_GUIDE.md` and `LIMITATIONS.md`. Student/course/supervisor fields intentionally remain blank. Native PowerPoint rendering and university rubric compliance still require the submitter's review. Render Free cold start can delay the demonstration; use the labeled recorded evidence rather than inventing an answer if the service is unavailable.

Previous releases, failed attempts and rollback backup evidence have been retained. No production rollback, secret rotation, model change or paid-plan upgrade was performed.
