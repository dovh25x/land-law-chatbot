# Deployment live — 22/10/2026

- Workflow: `Deploy application` run `39739696869`, kết quả **success**.
- Workflow ref: `06ddbf30ed665e3ec73d43eaabf44ae5a1f0b3cb`; source/runtime được deploy: `625e90e84079950e953267d1e4caaf0cb3e8c8e5`.
- Pages deployment: `32320f9c-f2d6-43d2-91f4-02621d596747` (URL `https://32320f9c.hanoi-land-law.pages.dev`), commit `625e90e`, production.
- Render deployment: `dep-dbcril8473hc73a10atg`, trạng thái `live`, commit `625e90e`.
- Public URL: `https://hanoi-land-law.pages.dev`.
- Corpus: `corpus-1afca764aa6692e0`; source gate `standing_verified_snapshot`; policy SHA256 `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`.
- Review metadata: `reviewed_at=2026-10-21T17:36:54.310157+00:00`, `reviewed_as_of=2026-10-21`, `legal_applicability_checked_at=2026-10-22`, `operational_expiry=null`, `whole_corpus_verified=false`, `source_fresh=false`, warning `source_partial_review`.
- Challenge: `session_challenge_mode=disabled`; HTML không tải script Turnstile và không có token.
- Public acceptance: `navigation.json` pass cho desktop 1440, mobile emulated 390/320; `generation.json` pass với model `openai/gpt-oss-120b`, 1 LLM call cho câu đầu, 1 call cho follow-up, citation client-side, reload/delete, server history `410`, session isolation.
- `report_matches_configuration=false` và `report_matches_corpus=false` trong artifact là do `/api/v1/evaluations/latest` vẫn trỏ báo cáo cũ ngày 17/10/2026 (SQLite/agentic), không phải runtime mismatch; runtime fingerprint thực tế là `07fc4e98e8ca25140012c6939db98cef7c8f0110845b94cef58d27de2481c70b`.
- Giới hạn: kiểm tra responsive bằng trình duyệt headless/emulated mobile, không có thiết bị vật lý; acceptance không phải thẩm định pháp lý độc lập.
