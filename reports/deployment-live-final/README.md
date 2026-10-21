# Production deployment evidence — 2026-10-22

- Deploy workflow: run `39662923555`, conclusion `success`.
- Source: `2d9cf095e26498cce91aec3c18528c88f0912f6f` (PR #8 merge).
- Cloudflare Pages: `e9b41c4b-e83a-4143-a175-8faddce7d3c0`.
- Render: `dep-dbch8g7avr4c73clrepg`, status `live`.
- Live verifier: `scripts/verify_live_ui.mjs` passed at 1440/390/320; `navigation.json` and screenshots are the local run.
- Render deployment status receipt: `render-deploy.jsonl` (downloaded from workflow artifact `deployment-evidence`).
- Public smoke checks: `../qa/production-smoke-2026-10-22.json`.
- The workflow artifact also contains the same navigation JSON and screenshots; it is retained on GitHub for run `39662923555`.

`navigation.json` reports `report_matches_configuration:false` because that field compares the latest evaluation report, not the deployed runtime. The verifier separately requires `evaluation.active_configuration_sha256` to equal the tested local fingerprint and the run passed.
