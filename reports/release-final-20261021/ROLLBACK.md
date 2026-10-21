# Release and rollback — safe academic source lookup

Tested/deployed application commit: `bc5c0e9c6df2fb72d6cd6aaa110e8cabbdddb9fb`.
Render deployment: `dep-dbc93css728c73ed7t00`; Pages deployment: `a0721662-651d-4b8b-9de8-ec02e6059da2`.

Serving flags must remain `SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`, `ALLOW_STALE_GENERATION=false`. Never rotate credentials or enable generation as a recovery shortcut. Source-only mode is a restricted legal-excerpt lookup, not a validated generative chatbot.

## Retained recovery evidence

- Prior Render source/deploy and Cloudflare deployment IDs: `cloud-inspection.json`, `cloudflare-deployment.json`.
- Pre-deploy corpus/config backup SHA256 `2cce1e17af08b61165786ad88a12eab400c3a1439604a83aba235985e589ecd5`; retained locally under the ignored `data/backups/` directory. Receipt: `before-deploy-backup.json`.
- Exact backup restored into a new local PG16 database without conversations: `rollback-restore.json`. Cloud PG17 schema/role was inspected separately; local restore is not a cloud restore test.
- Previous corpus `corpus-a26bc99e541fbbe2` is retained. New corpus `corpus-1afca764aa6692e0` is staged immutably and activated only after matching receipts. See `corpus-publication.json` for actual activation.

## Preferred containment and recovery

1. Confirm public `/readyz` and `/api/v1/status` through `https://hanoi-land-law.pages.dev`. Check safe fingerprint and disabled generation; never send a test chat to diagnose availability.
2. For corpus problems, keep the tested safe application code. On the operator workstation, using the existing administrator connection in memory, invoke existing `Store.publish('corpus-a26bc99e541fbbe2')`. This changes only active/previous pointers and retains both corpora. The old corpus has no reviewed receipt bundle; therefore the safe source-only API must return no reviewed excerpts. This is expected fail-closed behavior, not a promise of equivalent coverage.
3. Recheck readiness, status, empty reviewed catalog and unsigned-ingress rejection. Do not synthesize legal claims while restoring coverage.
4. For a broken frontend, redeploy the tested safe SHA using `scripts/deploy.py frontend --commit bc5c0e9c6df2fb72d6cd6aaa110e8cabbdddb9fb`. For a failed Render deployment, monitor/resume its existing deployment ID before starting another; redeploy the tested safe SHA if necessary.
5. Older Render/Pages deployments are retained as evidence, but pre-source-mode code is **not certified** to preserve the new scoped catalog behavior. Do not automatically activate an older code version just because it was previously live. If safe code cannot serve, report downtime and use the offline verified-source demonstration; do not restore unsafe generation.
6. If actual database corruption requires restore, first verify the checksum and restore the corpus-only backup into a new isolated database. Do not overwrite the serving database, drop tables, restore server conversation history, or reintroduce a multi-project corpus. A production restore requires a separate reviewed recovery operation.

## Repeatable release commands

The actual commands and outcomes are recorded in Git/CI/deployment receipts. Credentials are loaded from existing environment configuration and are never included below.

```bash
git push origin release/final-submission-20261021
gh workflow run ci.yml --ref release/final-submission-20261021
# Only after CI succeeds for the exact SHA and main has not moved unexpectedly:
git push origin release/final-submission-20261021:main
.venv/bin/python reports/release-final-20261021/configure_safe_render.py
.venv/bin/python scripts/deploy.py backend --commit bc5c0e9c6df2fb72d6cd6aaa110e8cabbdddb9fb --receipt reports/release-final-20261021/render-deploy.jsonl
.venv/bin/python reports/release-final-20261021/publish_candidate.py
.venv/bin/python scripts/deploy.py frontend --commit bc5c0e9c6df2fb72d6cd6aaa110e8cabbdddb9fb
```

These are an audit trail, not a script to rerun wholesale. The configuration/publication scripts refuse to overwrite existing receipts. Do not repeat a live pilot or duplicate an in-progress deployment. No production rollback was executed during this release.
