# Báo cáo bàn giao cuối — Trợ lý pháp luật đất đai Vành đai 4 Hà Nội

- **Ngày:** 22/10/2026
- **Nhánh:** `mvp/final-optimization`
- **Pull request:** [#11](https://github.com/dovh25x/land-law-chatbot/pull/11)
- **Runtime đã deploy:** `625e90e84079950e953267d1e4caaf0cb3e8c8e5`
- **Commit bằng chứng triển khai:** `c4eaf0bf0ea84eb8eb17adbdb0ee9622bb511119`
- **Trạng thái:** demo đã deploy và acceptance công khai đạt; **chưa đạt tuyên bố “nguồn đã kiểm chứng đầy đủ”** vì các finding pháp lý L01/L02 bên dưới.

## 1. Tóm tắt điều hành

Đã hoàn thiện một pipeline **Simple Conversational RAG** duy nhất: câu hỏi xã giao được phân loại và trả lời tất định trước khi chạm corpus; câu hỏi pháp luật mới dùng retrieval, evidence đã review và citation. Không đổi model, embedding, hosting Free, không thêm agentic RAG, reranker, fine-tuning, GIS hoặc pipeline thứ hai.

Đã thay policy nguồn ngắn hạn bằng **standing verified snapshot v2**, giữ nguyên receipt/checksum, toàn bộ 74 đoạn đã review và các cửa sổ pháp lý dài; chỉ cửa sổ ≤2 ngày trở thành standing. Policy v2 đã được kích hoạt trên production với 43 đoạn đủ điều kiện ngày 22/10/2026. Trạng thái công khai ghi rõ `review_mode=standing_verified_snapshot`, `source_fresh=false`, `warning=source_partial_review`, `whole_corpus_verified=false` và không còn `operational_expiry`.

Đã chạy bộ đánh giá khóa 12 ca: 4 xã giao không gọi Groq, 5 pháp luật có retrieval + Groq, 3 kiểm tra an toàn tất định. Live chạy đủ 5/5 ca pháp luật với **5 request, 10.442 token thực tế**. Kiểm tra tự động đạt **4/5**; đọc thủ công đạt **4/5 task success**, **3/5 grounded**, **0/5 false abstention**. L01 và L02 là finding pháp lý phải sửa trước khi tuyên bố chất lượng.

## 2. Thay đổi chính

### 2.1. Hội thoại và phạm vi

- Phân loại xã giao tất định trước khi đọc store/corpus; xã giao không retrieval, không citation, không gọi Groq.
- Câu hỏi ngoài phạm vi được chuyển về Vành đai 4 Hà Nội và đất đai; không trả lời code, tư vấn ngoài lĩnh vực.
- Giữ contract `multilingual-e5-small-onnx-q8-window-v1`, 384 chiều và Groq `openai/gpt-oss-120b`.
- Không xác định thửa đất, không tính tiền, không kết luận quyền lợi cá nhân; câu trả lời thiếu dữ kiện phải hỏi lại hoặc nêu điều kiện.

### 2.2. Standing snapshot v2

- Policy v2 SHA256: `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`.
- Giữ nguyên cohort receipt và checksum của policy v1 `015e33634ae920889271bbfcdf1a3e20977116b21c6c10be4face0c962d8d220`.
- 10 tài liệu, 74 đoạn reviewed, 42 đoạn standing, 6 legal windows; 43 đoạn đủ điều kiện ngày 22/10/2026.
- Biên đã kiểm tra: 22–25/10 = 43; 28/10 và 01/11 = 42; 01/01/2025 = 20. Rollback về v1 đã kiểm tra trong môi trường cô lập.
- Kích hoạt v2 từ chối nếu thiếu receipt, thiếu đoạn reviewed, đoạn không reachable, cohort v1 không khớp hoặc có policy v2 xung đột.
- Văn bản lịch sử như `qd-10-2026-hanoi` vẫn có trong thư viện nhưng có `effective_to=2026-04-02`; admission theo ngày không dùng đoạn hết hiệu lực làm căn cứ.

### 2.3. Challenge, phiên và quota

- Demo dùng `SESSION_CHALLENGE_MODE=disabled`: chỉ bỏ browser challenge. Session, bearer token, expiry, signed ingress, quota phiên/IP, concurrency, body limit, idempotency và LLM/token budget vẫn giữ.
- Production-safe `turnstile` vẫn được hỗ trợ; frontend chỉ tải Turnstile khi có site key.
- Thêm quota chat theo IP/ngày, độc lập với tạo phiên. Production đặt `PUBLIC_DAILY_IP_CHAT_LIMIT=30`; IP lấy từ ingress đã ký, `TRUST_PROXY_HEADERS=false`, không tin header client.
- Các giới hạn production đang bật: `MAX_CONCURRENT_REQUESTS=2`, `PUBLIC_DAILY_LLM_LIMIT=100`, `PUBLIC_DAILY_TOKEN_LIMIT=100000`, `EXECUTION_MODE=simple_rag`, generation 120B.

### 2.4. API, status và giao diện

- `/api/v1/status` và `/readyz` trả review mode, `reviewed_at`, `reviewed_as_of`, `legal_applicability_checked_at`, `operational_expiry`, `whole_corpus_verified`, policy SHA và warning.
- Thư viện nguồn lọc theo policy/ngày; không hiển thị đoạn hết hiệu lực như căn cứ hiện hành.
- UI có review notice, citation mở được nguồn, lịch sử chỉ trong IndexedDB 7 ngày; server không lưu messages/answer cache/trace chi tiết.
- Đã sửa hai lỗi triển khai chỉ thuộc workflow: (a) không export `SESSION_CHALLENGE_MODE` toàn job làm test Turnstile chạy sai mode; (b) site key Turnstile bị lọt vào build disabled do biểu thức GitHub Actions. Bản sửa không đổi runtime.

## 3. Kiểm thử

| Hạng mục | Lệnh / nguồn | Kết quả |
|---|---|---|
| Backend | `.venv/bin/python -m pytest -q` | **618 passed** |
| Frontend unit | `npm --prefix frontend test` | **29 passed** |
| Frontend build | `npm --prefix frontend run build` | **pass** |
| Playwright local | `npm --prefix frontend run test:e2e` | **36 passed** desktop/mobile |
| Secrets | `.venv/bin/python scripts/check_secrets.py` | **pass** |
| Preflight 12 ca | `scripts/evaluate_demo_suite.py` | xã giao 4/4, an toàn 3/3, retrieval 5/5; **0 Groq**, 5 ca pháp luật `NOT RUN` |
| Live 12 ca | cùng runner, `--live` | 5/5 ca pháp luật chạy; **5 request**, **10.442 token** |
| CI `c4eaf0b` | GitHub Checks run `39740823792` | **success**: backend, frontend, image; frontend rerun một lần sau khi npm registry trả **503** tạm thời |
| Deploy workflow | run `39739696869` | **success**; navigation + public chat pass |

Preflight dùng candidate v2, không gọi model; cả 5 ca pháp luật được giữ `NOT RUN` cho đến khi có phê duyệt live. Không dùng fixture thay cho live.

## 4. Đánh giá live

### 4.1. Ngân sách và attempt

| Lần | Trạng thái | Request | Token thực tế | Ghi chú |
|---|---|---:|---:|---|
| Attempt 1 | dừng do lỗi harness | 1 confirmed + 1 reserved | 2.325 | `RuntimeError: Event loop is closed`; ledger giữ nguyên |
| Replacement | hoàn tất | 5 | 10.442 | 5 request/15.000 token được duyệt riêng |
| **Tổng confirmed** |  | **6** | **12.767** | Attempt 1 còn 3.000 token reserved chưa xác nhận response |

- Suite khóa SHA256: `1423aa3023d3079bea32c6fa16d13448fd69f15eea14d97897ccb315d8e97c3d`.
- Raw live SHA256: `3ec023bce8a0f2d912e688f1a765a3877f09d7fb5aedb1edd8625fa30892b84c`.
- Reviewed artifact SHA256: `7aa3bca7d78a5e68c08992ffb5e3bff9e9cddf7259bc3c6af44529b5421c8556`.
- Không retry, không repair trong cùng attempt; không sửa prompt sau khi thấy kết quả.

### 4.2. Kết quả từng ca pháp luật

| Ca | Auto | Task success | Grounded | Finding |
|---|---|---|---|---|
| L01 | pass | **false** | **false** | Điều kiện thứ hai dẫn sai `[S3]`/`[S5]` (Điều 111/98, không phải Điều 95) và thêm “không vi phạm quy định về cư trú” không có trong nguồn. |
| L02 | pass | true | **false** | Đúng hướng nhưng dẫn “khoản 1 Điều 95” thay vì khoản 2; thêm “phương án bồi thường được phê duyệt” và Điều 107/81/82 không có trong evidence. |
| L03 | pass | true | true | Đúng 12 tháng cho thu hồi trên 70% đất nông nghiệp, không phải di chuyển; phần Lưu ý nhầm nhãn Nghị định 49/QĐ40. |
| L04 | pass | true | true | Đúng Điều 21 QĐ40 về bán căn hộ chung cư tái định cư/giao đất ở; không nêu số tiền. |
| L05 | **fail** | true | true | Từ chối tính số tiền, hỏi thêm dữ kiện; auto fail vì regex bắt cụm phủ định “đủ chắc chắn” — false positive. |

**Đọc thủ công: 4/5 task success, 3/5 grounded, 0/5 false abstention.** Auto-check 4/5 không thay thế đọc ngữ nghĩa: L01 cho thấy auto-check có thể pass dù citation không đúng nghĩa.

### 4.3. Giới hạn đánh giá

- Một lần chạy, 5 câu pháp luật; không phải benchmark diện rộng.
- Không dùng RAGAS hoặc LLM judge độc lập; không có thẩm định pháp lý độc lập.
- Kết quả chỉ là đánh giá kỹ thuật của assistant, không phải tư vấn/ chứng nhận pháp lý.
- Không chạy lại sau khi phát hiện L01/L02 để tránh chọn kết quả đẹp hoặc làm sai lệch suite đã khóa.

## 5. Phát hành, CI và deployment

- PR #11: `https://github.com/dovh25x/land-law-chatbot/pull/11`.
- Runtime được deploy: `625e90e84079950e953267d1e4caaf0cb3e8c8e5` (gồm `a1144d0` và bản sửa runner live).
- Deploy workflow: run `39739696869`, **success**.
- Pages deployment: `32320f9c-f2d6-43d2-91f4-02621d596747` (short `32320f9c`), commit `625e90e`, URL `https://32320f9c.hanoi-land-law.pages.dev`; production alias `https://hanoi-land-law.pages.dev`.
- Render deployment: `dep-dbcril8473hc73a10atg`, trạng thái `live`, commit `625e90e`.
- Corpus: `corpus-1afca764aa6692e0`.
- Policy v2 active: `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`; 43 đoạn đủ điều kiện.
- Runtime fingerprint: `07fc4e98e8ca25140012c6939db98cef7c8f0110845b94cef58d27de2481c70b`.

### 5.1. Trạng thái production

`GET /api/v1/status` trả:

- `corpus_release=corpus-1afca764aa6692e0`
- `session_challenge_mode=disabled`
- `source_fresh=false`; `warning=source_partial_review`
- `source_gate.mode=standing_verified_snapshot`
- `source_gate.reviewed_at=2026-10-21T17:36:54.310157+00:00`
- `source_gate.reviewed_as_of=2026-10-21`
- `source_gate.legal_applicability_checked_at=2026-10-22`
- `source_gate.operational_expiry=null`
- `source_gate.whole_corpus_verified=false`
- `source_gate.eligible_passages=43`

Không có tuyên bố “legally current” chỉ vì snapshot tồn tại.

### 5.2. Acceptance công khai

Workflow `39739696869` chạy qua public Pages ingress:

- Navigation: pass desktop 1440, mobile emulated 390/320; 60 tài liệu; source access; không horizontal overflow.
- Chat: pass; model `openai/gpt-oss-120b`; 1 LLM call cho câu đầu, 1 call cho follow-up; citation client-side; reload/delete; server history trả `410`; session isolation.
- Challenge disabled: `turnstile_token_observed=false`, `turnstile_script_requested=false`; không tải script Turnstile.
- Artifact: `reports/deployment-chat/generation.json`, `reports/deployment-live/navigation.json` + ảnh desktop/mobile.

### 5.3. Điểm cần lưu ý

`/api/v1/evaluations/latest` vẫn trả báo cáo cũ ngày 17/10/2026 (SQLite/agentic), nên acceptance ghi `report_matches_configuration=false`, `report_matches_corpus=false`. Đây là metadata đánh giá cũ, không phải runtime mismatch; runtime fingerprint thực tế khớp `07fc4e...`. Cần publish báo cáo đánh giá hiện hành nếu muốn endpoint này khớp.

## 6. Phê duyệt

- Phê duyệt live evaluation 5 request/15.000 token, tuần tự, không retry/repair: **đã có**.
- Phê duyệt allocation thay thế 5 request/15.000 token sau lỗi harness: **đã có**.
- Phê duyệt production deploy, tắt browser challenge cho demo, kích hoạt policy v2 và chạy public acceptance: **đã có**.
- Không có phê duyệt mới cho việc sửa prompt/verifier rồi chạy lại; các finding được giữ nguyên làm bằng chứng.

## 7. Rollback

- **Application:** deployment trước release là `2d9cf095e26498cce91aec3c18528c88f0912f6f` (Pages `e9b41c4b-e83a-4143-a175-8faddce7d3c0`, Render `dep-dbch8g7avr4c73clrepg`). Baseline rollback đã kiểm tra trước đó: `422d363` (Pages `10378b38-a773-4b07-a6d3-839ac016babd`, Render `dep-dbcer729lscs739d2pkg`).
- **Không rollback về Pages `c21b7e26`**: bản này có site key Turnstile lọt vào build disabled; chỉ dùng để tham chiếu lịch sử.
- **Policy:** giữ v1 nguyên byte tại `reports/source-review-20261022/source-gate-20261022.json`; kích hoạt lại v1 vào `source_gate:<release>`, xác nhận `mode=scoped_receipts`, chạy lại boundary tests. Không xóa receipt/không sửa checksum.
- **Database:** không drop; nếu cần restore, restore vào database riêng và kiểm tra corpus/fingerprint trước khi chuyển traffic.
- Rollback không phục hồi server history (server không lưu) hoặc corpus đa dự án.

## 8. Blocker và khuyến nghị

### P0 — chặn tuyên bố chất lượng pháp lý

- **L01:** câu trả lời đưa điều kiện không có trong nguồn (“không vi phạm quy định về cư trú”) và dẫn `[S3]`/`[S5]` cho Điều 95 trong khi đây là Điều 111/98. Đây là lỗi điều kiện + citation, có thể làm người đọc hiểu sai eligibility. **Không được tuyên bố “legal quality passed”** cho đến khi sửa prompt/verifier và chạy lại bộ đã khóa với phê duyệt mới.
- Đây là P0 **đối với claim chất lượng**, không phải sự cố bảo mật/khả dụng. Demo đã deploy với disclaimer và không đưa ra quyền lợi cá nhân.

### P1 — cần xử lý trước khi mở rộng public legal service

- **L02:** dẫn “khoản 1” thay vì khoản 2 và thêm điều kiện “phương án bồi thường được phê duyệt”/Điều 107/81/82 không có evidence.
- **L03:** đúng số liệu nhưng phần Lưu ý gọi nhầm Nghị định 49/2026 thay vì QĐ40/2026.
- **Nguồn:** `source_fresh=false`, `whole_corpus_verified=false`, chỉ 43 đoạn reviewed đủ điều kiện; không được gọi là “toàn bộ corpus đã kiểm chứng” hoặc “legally current”.
- **Đánh giá:** `/api/v1/evaluations/latest` còn báo cáo cũ; chưa có independent legal review.
- **Vận hành:** chưa load-test quota IP 30/ngày, concurrency 2 và cold start Free.

### P2 — cải thiện

- L05 auto-check false positive do regex bắt cụm phủ định “đủ chắc chắn”; cần test theo ngữ nghĩa hoặc loại trừ phủ định.
- Acceptance mobile là emulated, không có thiết bị vật lý.
- Bộ 12 ca nhỏ; không dùng RAGAS/LLM judge theo thiết kế.

### Khuyến nghị trước lần public tiếp theo

1. Sửa claim-level verifier để kiểm tra citation đúng **điều/khoản/đoạn** và loại điều kiện không có nguồn; thêm regression L01/L02.
2. Khóa bộ đánh giá mới trước khi sửa prompt; xin phê duyệt ngân sách nếu chạy lại model; giữ mọi attempt.
3. Publish báo cáo evaluation hiện hành hoặc ẩn endpoint cũ để tránh hiểu nhầm.
4. Có thẩm định pháp lý độc lập trước khi gọi là dịch vụ tư vấn; nếu chỉ demo, giữ disclaimer và cân nhắc bật lại Turnstile.

## 9. Artifact và commit

- Runtime/evidence: `a1144d0` (runtime), `625e90e` (runner/test + preflight source), `fd0595e` (v2 candidate/preflight evidence), `1e1b470` (replacement live), `56f23ec` (reviewed live evidence), `a2e75a4` + `06ddbf3` (workflow fixes), `c4eaf0b` (deployment evidence).
- Policy: `reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json`; build evidence `reports/source-review-20261022/standing/build-evidence-20261022.json`.
- Preflight: `reports/evaluation/demo-v1-20261022/preflight.json`.
- Live raw/reviewed/ledger: `reports/evaluation/demo-v1-20261022/live-20261022-replacement-*.json`; attempt 1: `reports/evaluation/demo-v1-20261022/attempts/`.
- Deployment: `reports/deployment-live/`, `reports/deployment-chat/`, `reports/deployments/`.
- CI: backend **618 passed**; frontend unit **29 passed**; local Playwright **36 passed**; deploy workflow **success**. Checks run `39740823792` tại `c4eaf0b`: **backend, frontend, image đều success**; frontend được rerun một lần do npm registry trả **503** tạm thời, không phải lỗi code. PR #11 đủ điều kiện merge theo check này.

Không có secret, token, nội dung hội thoại hay dữ liệu cá nhân trong báo cáo này.
