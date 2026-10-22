# FINAL RESULT — Bounded Agentic RAG production release

- **Ngày:** 22/10/2026
- **Quyết định:** **GO có điều kiện** cho MVP đại học. Hệ thống đang chạy `agentic_rag` trên production; không có lỗi P0 nào được tái hiện, nhưng còn defect P1 về false abstention và L03 chưa chạy live.
- **Báo cáo metrics đầy đủ:** `reports/evaluation/agentic-rag-final/metrics.json`

## 1. Trạng thái deploy

- Production: https://hanoi-land-law.pages.dev/
- Runtime: `agentic_rag`; frontend và backend đều ở source `b1c10f4bad6b89f1d555eb08f5216b4b285be6d6`.
- Merge PR #11: `5223937d28d9042e47521f41ce4c2b7ecd9ee126`.
- Render deploy: `dep-dbd26u2vcj2c739dtck0` — **live**, commit `b1c10f4`.
- Pages deploy: `636baf63-fde3-44c6-a26f-91f62d8cf970` — commit `b1c10f4`.
- Hotfix production: `b1c10f4` sửa lỗi placeholder PostgreSQL ở nhánh retrieval admitted; không sửa corpus/policy.
- CI: Checks `39791588047` tại merge `5223937` — **success**; hotfix `b1c10f4` deploy workflow `39799450935` — **success**.
- Config fingerprint sau hotfix: `44d118d8dca10fdb19349631c608269ace47a26145e1ea997e0fda7e6838090f`.

## 2. Bằng chứng tool calling thật

- Pre-deploy: 6 tool execution thật trên các ca legal, không có tool execution nào thất bại.
- Production smoke social: `mode=agentic_rag`, `llm_calls=1`, `tool_calls=0`.
- Production smoke legal L02: `mode=agentic_rag`, `llm_calls=2`, `tool_calls=1`; trace có `search_legal_evidence`; retrieval lấy 4 đoạn reviewed; 2 citation thật (`49/2026/NĐ-CP` Điều 11 và `31/2024/QH15` Điều 95) với URL công báo.

## 3. Kết quả T01/T02

| Ca | Trạng thái | Kết quả |
|---|---|---|
| T01 — quy hoạch/chỗ ở mới | `clarification_needed` | Đã gọi retrieval, có 2 citation đúng (NQ 254/2025 Điều 3; QĐ 40/2026 Điều 21). Trả về trích đoạn thật và hỏi thêm giấy tờ/giai đoạn. Chưa đạt câu trả lời có điều kiện đầy đủ → false abstention P1. |
| T02 — “đất tôi ở thuộc dự án Vành đai 4” | `clarification_needed` | Kế thừa ngữ cảnh lượt trước; 2 tool execution (search + open); 2 citation đúng; không dùng tin dự án để chứng minh quyền lợi. Vẫn là clarification, chưa phải câu trả lời có điều kiện đầy đủ → P1. |

## 4. Chất lượng L01/L02/L03

- **L01:** `answered`; 3 citation đúng điều (Điều 95, Điều 111 khoản 4, Điều 98); **không** tái hiện điều kiện “không vi phạm quy định về cư trú”; không nêu số tiền hay quyền lợi cá nhân. Câu trả lời còn thiếu một số điều kiện của Điều 95 → đánh giá **partial**, không phải lỗi điều kiện bịa.
- **L02:** chạy production; `clarification_needed`, 2 citation đúng (NĐ 49/2026 Điều 11; Luật Đất đai Điều 95); không có điều kiện bịa, không có số hiệu sai. Chưa trả lời trực tiếp câu hỏi “có quyết định giao đất” → false abstention P1.
- **L03:** **NOT RUN**. Hai lần thử pre-deploy bị provider 400/429 trước khi sinh câu trả lời; budget đã dùng hết 20/20 request nên không chạy thêm. Không có kết luận chất lượng cho L03.
- **Không tái hiện unsupported legal claim nghiêm trọng nào**, nhưng **không tuyên bố L01/L02/L03 đã đạt chất lượng đầy đủ**.

## 5. Metrics thật

### Pre-deployment — runtime 4fff5e1, 16 request thật

| Ca | Status | Request | Tool | Token | Latency |
|---|---|---:|---:|---:|---:|
| A01 social | answered | 1 | 0 | 751 | 1.011 ms |
| T01 | clarification | 3 | 1 | 3.662 | 18.013 ms |
| T02 | clarification | 3 | 2 | 5.787 | 9.491 ms |
| L01 | answered | 3 | 1 | 3.161 | 11.719 ms |
| L02 | limited (429) | 3 | 1 | 735 | 7.992 ms |
| L03 | limited (429) | 3 | 1 | 756 | 9.561 ms |

- Tool Selection Accuracy: **6/6 routing turn** (A01 đúng không tool; 5 ca legal đều chọn tool).
- Tool Execution Success Rate: **6/6**.
- Task success: **1/6 full**, **3/6 partial**, **2/6 error/not run**.
- Grounded: **1/5 câu legal trả lời đầy đủ có nguồn**, **2/5 clarification có trích đoạn thật**, **2/5 không có câu trả lời**.
- Citation Correctness: **7/7 citation đúng văn bản/điều**.
- Unsupported Legal Claim Count: **0**.
- False Abstention: **2/5 ca legal** (T01, T02); L02/L03 không tính vì lỗi provider.
- Latency: median **9.526 ms**; p95 small-sample = **18.013 ms** (giá trị lớn nhất, mẫu 6).
- Provider errors: **4 HTTP 400** ở tool-decision thứ hai (đã sửa bằng hotfix `d4c153a` bỏ lượt tool-decision thứ hai) và **2 HTTP 429**.
- Tổng token xác nhận: **14.852**.

### Production smoke — runtime b1c10f4, 4 request thật

| Lượt | Status | Request | Tool | Token | Latency |
|---|---|---:|---:|---:|---:|
| Social | answered | 1 | 0 | 749 | 6.862 ms |
| Legal L02 lần 1 | turn_failed (lỗi Postgres, đã sửa) | 1 | 0 | không có usage | 32.333 ms |
| Legal L02 lần 2 | clarification_needed | 2 | 1 | 3.292 | 43.830 ms |

- Token xác nhận production: **4.041**.
- Tổng toàn release: **20/20 request**, **60.000 token reservation**, **18.893 token xác nhận**, 1 request lỗi không nhận usage (reservation 3.000 vẫn giữ).

### Retrieval offline

- 20 ca gold: **Recall@5 = 0,975**, **Admitted Evidence Recall@5 = 0,925**.
- Hai lượt hội thoại offline: **8/8 admitted** ở cả turn 1, turn 2 và follow-up.
- Nguồn: `reports/qa/ring4-retrieval-offline-current.json`, `reports/qa/phase-a-two-turn-diagnosis.json`.

## 6. Kiểm thử và hạ tầng

- Backend: **634 passed**.
- Frontend unit: **29 passed**; build pass.
- Playwright desktop/mobile: **36 passed** (chạy trước release; deploy workflow chạy lại build + navigation verification và pass).
- Secrets scan: pass.
- Session production: HTTP 201; chat SSE trả `result` bình thường sau hotfix.
- Không tắt Turnstile ngoài mode `disabled` đã được duyệt; ingress, bearer session, quota IP/session, concurrency, daily LLM/token limit vẫn giữ.

## 7. Corpus và policy

- Corpus: `corpus-1afca764aa6692e0`; policy standing v2 SHA `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`.
- 60 tài liệu, 7.396 chunk, 10 tài liệu có receipt, 74 đoạn reviewed, **43 đoạn admitted**.
- Không thêm, xóa, tạo receipt hay đổi policy trong đợt này.
- `ALLOW_STALE_GENERATION=false`; không có expiry 24h/72h/7d.
- Giới hạn: chưa có review cho Luật Nhà ở Điều 72, Luật Quy hoạch 2025, nhóm khiếu nại và nguồn vận hành Hà Nội; văn bản dự án chỉ là context.

## 8. Vấn đề còn lại

**P1:**
- False abstention: T01, T02 và L02 production trả clarification có trích đoạn thay vì câu trả lời có điều kiện đầy đủ.
- L03 chưa được chạy live; chất lượng chưa xác nhận.
- Mẫu 6 ca pre-deploy + 2 lượt production là quá nhỏ để kết luận chất lượng pháp lý rộng.

**P2:**
- `/api/v1/evaluations/latest` vẫn có thể hiển thị báo cáo historical không khớp runtime; cần cập nhật metadata hoặc ghi rõ historical.
- Provider Free Plan có thể trả 429/400; chưa load-test.
- Mobile acceptance trước đây là emulated, không phải thiết bị vật lý.

## 9. GO/NO-GO và rollback

**GO có điều kiện** cho mục tiêu MVP đại học: hệ thống thật đang chạy `agentic_rag`, tool calling hoạt động, social trả lời tự nhiên, legal query lấy được evidence đã review, citation đúng nguồn, không tái hiện unsupported entitlement, CI xanh, session/ingress/quota còn nguyên.

**Không** tuyên bố đạt chất lượng pháp lý đầy đủ hay thẩm định độc lập.

Rollback:
- Application: đặt `EXECUTION_MODE=simple_rag` và redeploy SHA `625e90e84079950e953267d1e4caaf0cb3e8c8e5` (bản Simple RAG ổn định trước release).
- Corpus/policy: giữ nguyên release `corpus-1afca764aa6692e0` và policy v2; không cần restore DB.
- Đã kiểm tra rollback mode trước đó; không drop dữ liệu, không xóa receipt.
