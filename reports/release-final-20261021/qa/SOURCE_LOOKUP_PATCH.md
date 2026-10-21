# Minimal verified-source fallback

Sau C02 độc lập INCOMPLETE, triển khai fallback đã được user cho phép: tra cứu đoạn nguồn được review, không phát sinh câu trả lời pháp luật bằng model.

## Behavior và ranh giới

`SOURCE_LOOKUP_ONLY=true` bắt buộc `GENERATION_ENABLED=false` qua Settings validation. API chat vẫn từ chối generation kể cả khi code caller dùng `model_copy`/assignment để bỏ qua validation. Không thay agent/provider/verifier, schema claims, corpus, receipts, embedding, migrations hoặc gold.

Giữ endpoints hiện có:

- `GET /api/v1/documents?as_of=YYYY-MM-DD`: mặc định ngày Việt Nam, chỉ metadata của văn bản có exact reviewed passages cho ngày đó; không catalog references ngoài review. Trả `source_lookup_only`, `as_of`, `verified_passage_count`, `whole_corpus_verified=false`.
- `GET /api/v1/documents/{id}?as_of=YYYY-MM-DD[&locator=...]`: chỉ trả các chunks được receipt gate chấp nhận đúng ngày, checksum và text digest; nguồn không đủ điều kiện trả 404. Không trả relations chưa được admission kiểm tra. Metadata nêu `whole_document_verified=false`, `review_as_of` và số passages.
- `/api/v1/status`: source-only capability, ngày mặc định; không quảng cáo citizen answers.
- `/readyz`: source lookup có DB/corpus có thể ready khi không có LLM key. Readiness là trạng thái dịch vụ; không thay legal/citation guard hoặc chứng nhận mọi ngày đều có nguồn.

Chỉ dùng active policy pinned receipts để đề cử chunk IDs; vẫn gọi `Store.scoped_source_reviews` kiểm latest review, trạng thái changed/unknown/stale, checksum và khoảng ngày. Truy xuất bounded exact chunk IDs, không load toàn corpus 7.396 embeddings. Public read vượt 256 candidate IDs sẽ fail closed. `Store.chunk` và checksum text được đối chiếu trước khi đưa excerpt ra response. Mode thường default false giữ library snapshot cũ.

UI giữ bố cục hiện có, thêm banner prototype/source-only, CTA thư viện, ngày đối chiếu và nhãn giới hạn từng đoạn. Source panel hiển thị các đoạn được review và đường dẫn nguồn/phiên bản; không gọi model. Ngày detail được pin theo metadata list. Lịch sử IndexedDB được giữ nguyên nhưng assistant text cũ được nhãn chưa xác minh lại; không render citizen-answer/citation controls như evidence mới. Source panel không dùng excerpt từ client history làm nguồn đã review.

## Tests và bằng chứng

| Kiểm tra | Kết quả thực tế |
|---|---|
| Targeted Python source-lookup + existing scoped gate + API | 56 passed, 11,87 giây; trong đó 13 source-lookup tests mới |
| Frontend unit | 16 passed; hai tests nhãn mode/source row mới |
| Frontend build | PASS, chạy lại sau history handling patch |
| Focused Playwright | 4 passed, 14,3 giây: hai cases × desktop/mobile |
| Actual source-only API, private SQLite với corpus/receipts đã review | PASS: 25 passages ngày 02/08/2024; 43 ngày 21/10/2026; chỉ một header QĐ40 ngày 22–23/10 |
| Actual source-only API, private PostgreSQL với runtime role | PASS: 43 ngày 21/10; một header ngày 22/10; 25 lịch sử; 413 SQL statements đều SELECT, không thay đổi DB |
| External LLM calls trong tests/acceptance | 0 |

Lần Python TestClient đầu trong sandbox bị treo sau test đầu; dừng SIGINT, exit130, giữ log. Chạy lại regression local qua cơ chế execution approval chính thức PASS; không thay test assertion hoặc runtime để vượt quyền.

Playwright mới dùng API fixtures, không phải public E2E. Actual source-only acceptance dùng HTTP TestClient và DB riêng, không phải Supabase/PostgreSQL benchmark. Root chạy full suite/CI/image theo commit cuối; các kết quả đó không nằm trong receipt targeted này.

QA sau đó đọc trực tiếp evidence của release owner: [full backend](../backend-full.log) **529 passed, 223,34 giây** trên Python 3.14; [full local Playwright](../frontend-e2e-full.log) **104 passed, 4,9 phút**; [Docker build](../docker-build-final.log) PASS, [memory probe](../docker-memory-final.log) **381,70703125 MiB**, dưới 512 MiB trên serving image Python 3.12 mới. Không dùng 516 Python 3.12 tests của image Phase 4 để tuyên bố đã chạy 529 tests trên image mới; CI sẽ có evidence riêng.

[PG acceptance receipt](source-lookup-pg-acceptance.json) dùng DB Docker riêng `landlaw_phase4_restore`, role `landlaw_phase4_runtime`, chỉ GET endpoints. Interceptor cấm mọi application SQL ngoài SELECT; số records trước/sau giữ nguyên 60 documents, 7.396 chunks, 11 source reviews. Role không superuser, không BYPASSRLS và không INSERT vào messages/traces/cache/releases/reviews. Không migration/restore/session writes trong lượt này. Đây là current source-only API PASS trên PostgreSQL local, vẫn không phải cloud deployment, public E2E, model inference hoặc PG retrieval Recall@5.

## Candidate identities

- Source-only SQLite: `dba699954ac85068b40f676eaa2c927065d81c406eda7b08a6665ffafc53e58e`.
- Source-only PostgreSQL configuration: `8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464`.
- Normal-mode SQLite của code mới: `f8104b9bff431a25af0803bc7fb350bc248843b7fbfae5ea33ca4352cb2b6286`.

Các fingerprint trên thay đổi theo code source và setting mode. C02 vừa chạy và Recall@5 lịch sử thuộc fingerprint `1697…`; không chuyển số liệu đó sang fingerprint source-only mới như một run chung.

## Files liên quan

`backend/landlaw/config.py`, `api.py`, `evaluation.py` (chỉ thêm mode vào fingerprint); `frontend/src/App.tsx`, `api.ts`, `ui.tsx`; `tests/test_source_lookup_mode.py`; `frontend/src/sourceLookup.test.ts`; `frontend/e2e/source-lookup.spec.ts`.

Chỉ source/review lookup PASS. Không có generated legal-answer PASS; không tự đạt READY cho cloud, public E2E hoặc coverage ngày 23/10. Artifact history, failed S06/C01/C02 và corpus giữ nguyên.
