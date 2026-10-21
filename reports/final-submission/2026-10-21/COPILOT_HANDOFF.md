# Copilot handoff — 21/10/2026

## Current identity

- Repository: `dovh25x/land-law-chatbot`
- Branch: `release/final-submission-20261021`
- HEAD: `220b2cf06f49b5c527c125da650a56428d657c65`
- Remote: `origin/release/final-submission-20261021` is up to date with HEAD.
- Working tree at handoff: clean, apart from the receipt rewrite caused by the
  offline verifier; that rewrite is restored to the committed Phase 4 receipt.
- Current release commit is also the SHA used by the successful GitHub Actions
  `Checks` run `39591242193` (backend, frontend, and image jobs all passed).

## What Codex completed

- Preserved the FastAPI/LangGraph/Groq GPT-OSS 120B and E5 ONNX Q8 384-dimension
  architecture and the source/citation guards.
- Completed and committed the source-only guarded release changes in `220b2cf`.
- Preserved historical evaluation attempts and limitations: S06 `FAIL`, C01
  `INCOMPLETE`, C02/C03 model pilots `NOT RUN`, and no final-runtime model
  correctness claim.
- Completed local evidence for backend/frontend regression, Docker image and
  memory checks, isolated PostgreSQL migration/role/backup-restore checks, and
  SQLite retrieval metrics. These are evidence-bound and are not being relabeled
  as legal answer accuracy.
- Exported the Vietnamese report and presentation:
  - [Final_Project_Report.pdf](../../submission-20261021/Final_Project_Report.pdf)
  - [Final_Project_Presentation.pptx](../../submission-20261021/Final_Project_Presentation.pptx)
  - [Final_Project_Presentation.pdf](../../submission-20261021/Final_Project_Presentation.pdf)
  - [Final_Submission_Package_996e1b43eb1f.zip](../../../dist/academic-release-20261021/Final_Submission_Package_996e1b43eb1f.zip)
- Recorded a public source-lookup deployment and browser evidence in the
  academic release package. That deployment intentionally has generation
  disabled and is not evidence for model-answer quality.

## Deliverable status

| Deliverable | Status | Evidence / boundary |
|---|---|---|
| Git commit and push | **DONE** | HEAD `220b2cf`; branch tracks origin |
| CI for release SHA | **DONE** | GitHub Actions run `39591242193`, all three jobs passed |
| Cloud deployment and rollback readiness | **PARTIAL** | Source-only cloud release and rollback/restore evidence exist; current HEAD is not the serving SHA |
| Real public end-to-end testing | **PARTIAL** | Public source lookup/browser checks exist; generative flow and model quality were not run |
| Final evaluation artifacts and metrics | **DONE (bounded)** | Retrieval/context/software metrics and failed attempts retained; answer accuracy/RAGAS/faithfulness remain NOT MEASURED |
| Vietnamese final report PDF | **DONE, pending student review** | Exported PDF; cover fields and institutional rubric still require human review |
| Presentation PPTX/PDF | **DONE, pending rehearsal** | Exported artifacts; presentation rehearsal is still required |
| Demo guide, README, limitations, submission bundle | **DONE, pending final review** | Present in `reports/final-submission/2026-10-21/` and `dist/academic-release-20261021/` |
| Git/deployment identity consistency | **PARTIAL / intentional mismatch** | Git candidate `220b2cf`; serving source-only candidate `ec5d9a9`; do not claim they are identical |

## Exact next tasks

1. Student reads the report and slides, fills cover metadata, and checks the
   university rubric/template.
2. Rehearse the demo using
   [DEMO_SCRIPT.md](DEMO_SCRIPT.md), explicitly presenting source-only mode and
   the retained failed/not-run evaluation cases.
3. Deliver the package with its checksums and separately provide any approved
   corpus/model assets; do not include secrets or unreviewed environment files.
4. If a current-SHA public deployment is required, obtain explicit approval,
   then deploy/verify `220b2cf` through the normal release process and record a
   new SHA-bound receipt. Do not enable generation or spend Groq quota without
   a separate approved evaluation protocol.
5. Submit through the university system and retain the receipt.

## Blockers requiring user input

- Cover information: student name, student ID, supervisor, course, and required
  institutional template/rubric.
- Whether the current source-only public deployment is acceptable for the demo,
  or whether approval is available for a current-SHA deployment.
- Whether any generative pilot is authorized and funded; no quota is available
  to assume a final model-quality pass.
- Submission channel and final deadline/template confirmation. Existing
  repository checklists intentionally do not invent these details.

## Time estimate

- Student review, cover completion, rubric check, and rehearsal: approximately
  2–4 hours.
- Final archive/secret/hash/link review and submission: approximately 0.5–1 hour.
- Current-SHA cloud promotion, if approved and unblocked: approximately 4–8
  hours, excluding provider/quota/restore delays.

## Final acceptance criteria

- Student-approved report and slides with required cover metadata.
- Submission archive opens on another machine, checksums verify, and contains no
  secrets or private runtime state.
- Demo labels source-only evidence, fixtures, historical failures, and
  unmeasured model quality without overstating results.
- If cloud status is reported, the report names the exact serving SHA and
  distinguishes it from the Git candidate; rollback tuple and restore evidence
  are attached.
- No claim of generative legal-answer correctness, public generative E2E, or
  legal advice is made without newly recorded evidence and explicit approval.
