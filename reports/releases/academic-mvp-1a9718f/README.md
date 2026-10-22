# Academic MVP — PR #13 public release

**Kết luận:** đã merge, deploy và xác minh dịch vụ public. Đủ điều kiện công bố/nộp MVP học thuật theo phê duyệt của chủ dự án; **không** phải legal-quality acceptance hoặc chứng nhận pháp lý.

## 1. Phiên bản và phê duyệt

- [PR #13](https://github.com/dovh25x/land-law-chatbot/pull/13): **MERGED**, HEAD trước merge `ae2a6753013808697725f230bf3e01064dc0cf1e`.
- Merge/source SHA triển khai: **`1a9718f03ed261f3511598488ab273b6bf5e0b92`**. Tree merge giống HEAD đã xanh; không thay runtime sau pilot.
- Chủ dự án phê duyệt phát hành ngay với pilot PARTIAL, chỉ giữ blocker deployment/security/grounding safety nghiêm trọng; không yêu cầu hoàn tất evaluation diện rộng.
- Không đổi corpus, receipt, policy, migration, model/provider hoặc hosting; không re-embed, không tạo tài nguyên trả phí.
- Các commit tài liệu/bằng chứng sau release không phải SHA ứng dụng và không tự kích hoạt redeploy.

## 2. CI và deployment

| Thành phần | Bằng chứng |
|---|---|
| CI SHA merge | [Checks 39841882015](https://github.com/dovh25x/land-law-chatbot/actions/runs/39841882015): backend/frontend/image **SUCCESS** |
| Software | Backend **653 passed**, frontend unit **30 passed**, Playwright **38 passed**; build/secrets scan đạt, npm audit 0 vulnerability |
| Workflow triển khai | [Deploy application 39842159622](https://github.com/dovh25x/land-law-chatbot/actions/runs/39842159622): **SUCCESS**, `source_sha` ghim đúng merge, `verify_public_chat=false` |
| Cloudflare Pages | **`9a00398a-eb3f-4283-987a-e2fe6d34d090`**, SHA `1a9718f03ed261f3511598488ab273b6bf5e0b92`, stage `success` |
| Render | **`dep-dbd6dukipgvc73e7rsm0`**, cùng SHA, status `live`, plan `free`, auto-deploy `off` |
| Public | **https://hanoi-land-law.pages.dev/** |
| Frontend bundle | `/assets/index-Dvu57KE3.js`; SHA-256 `64ff9922baca5958ac8d2e8ab4f161861e7adc26bc88d1eaa156eb94298fff28` |

Pages canonical deployment và Render live commit được đối chiếu qua management API chỉ đọc; bundle public khớp deployment URL `https://9a00398a.hanoi-land-law.pages.dev`. Workflow đã chạy lại các bước kiểm tra vốn có; không thêm evaluation model.

## 3. Runtime, corpus và nguồn

Đã kiểm tra cấu hình thực tế trên Render, không suy runtime từ field `mode` của báo cáo evaluation lịch sử:

```text
EXECUTION_MODE=agentic_rag
GENERATION_ENABLED=true
SOURCE_LOOKUP_ONLY=false
ALLOW_STALE_GENERATION=false
GROQ_MODEL=openai/gpt-oss-120b
SESSION_CHALLENGE_MODE=disabled
PUBLIC_DAILY_IP_CHAT_LIMIT=30
```

| Identity | Giá trị |
|---|---|
| Active corpus | `corpus-1afca764aa6692e0` |
| Standing policy SHA-256 | `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d` |
| Runtime configuration SHA-256 | `977bbd4ec571f87d0c2937b8a514c57aae283db35a8cdbe0397baaa358ecb834` |
| Storage | PostgreSQL/pgvector hiện có; 60 tài liệu trong thư viện |
| Source gate | `standing_verified_snapshot`, usable, **43 admitted passages**, `whole_corpus_verified=false` |
| Freshness | `source_fresh=false`, warning `source_partial_review`; không làm mới receipt giả |

Runtime fingerprint public khớp tính toán từ source đã deploy cho PostgreSQL. Fingerprint cũ `44d118d8…` không còn là runtime hiện tại. `/api/v1/evaluations/latest` vẫn có báo cáo lịch sử không khớp cấu hình/release; giữ cảnh báo này, không gán báo cáo cũ cho runtime mới.

Bounded Agentic RAG, source-gated retrieval, citation/reference validation và applicability guard đã triển khai. Guard từ chối không phải bằng chứng mọi diễn giải đúng ngữ nghĩa.

## 4. Public smoke — zero Groq

Kiểm tra thực tế sau deploy, 22/10/2026 UTC; không intercept/mock public API:

- Website/bundle, `/healthz`, `/readyz`, `/api/v1/status`, thư viện và detail Luật Đất đai: **200**.
- Source link chính thức của Luật Đất đai: **200**; panel nguồn và liên kết mở được.
- Desktop **1440 px**, mobile emulation **390/320 px**: navigation, source panel, không tràn ngang, không có browser/page error.
- Bốn gợi ý đúng nội dung; click điền/focus composer, **0 POST chat**.
- Session tạo **201**, token hợp lệ **200**, bearer sai **404**, server history **410**.
- Reload/xóa history, TTL loại bản ghi hết hạn và xóa history không mất session: **PASS**.
- Citation rendering/panel của một kết quả pilot cũ lưu vào IndexedDB của browser tạm: **PASS**. Đây là kiểm tra tương thích history/UI, **không** phải một câu trả lời mới từ model.
- Direct Render API thiếu chữ ký hoặc chữ ký giả bị từ chối; Pages ingress hoạt động, method ngoài allow-list **405**. Các quota/session/ingress code không thay đổi; không cố tình làm cạn quota để thử 429.
- Cấu hình anonymous session hiện có giữ `disabled`; không bật/tắt challenge trong release.

**Live legal-generation smoke: NOT RUN. Groq usage trong release: 0 request, 0 token.** Allocation pilot trước đã bị chặn và chưa có bằng chứng quota Free/affordability cho request bổ sung; không mở allocation mới, không tự retry hoặc dùng paid credits. Không khẳng định đã kiểm tra full end-to-end public legal answer.

## 5. Bốn câu hỏi đã triển khai

1. Trợ lý này có thể giúp gì?
2. Có sổ đỏ, khi Nhà nước thu hồi đất ở thì điều kiện được bồi thường là gì?
3. Khi bị thu hồi đất nông nghiệp, người dân có thể được hỗ trợ những gì?
4. Nếu bị thu hồi đất ở và phải chuyển nhà, điều kiện được bố trí tái định cư là gì?

## 6. Evaluation và giới hạn giữ nguyên

- [Pilot hậu hotfix](../../evaluation/agentic-rag-post-hotfix-pilot/README.md): **PARTIAL**, A01 PASS; T01 PARTIAL/false abstention; T02 bị chặn trước HTTP, L02 NOT RUN. **3 request**, **4.738 token confirmed**, 9.000 reservation; request cuối T01 dùng 3.242 token > reservation phẳng 3.000. Không đổi các case chưa chạy thành PASS.
- Pilot có 2/4 ca hoàn tất, không đại diện thống kê; chưa có substantive legal answer để chấm grounded-answer/faithfulness. Citation identity 2/2 không thay semantic/legal review.
- [Offline retrieval hậu hotfix](../../evaluation/agentic-rag-legal-answer-hotfix/README.md#6-retrieval-hậu-hotfix--offline-zero-quota): Recall@5 **0,975**, Admitted Evidence Recall@5 **0,925**; cùng corpus/gold/policy/E5, JSON trùng byte với benchmark trước. Không suy ra retrieval đã cải thiện.
- **Đính chính diễn giải mẫu số trong report hotfix cũ:** hai giá trị trên là **macro mean trên 20 case**, không phải 39/40 và 37/40 gold chunk. Tính trực tiếp từ JSON đã khóa: 23 gold chunk, raw hit 22/23, admitted 21/23; top-5 hit 20/20, admitted hit **19/20** (S02 không còn gold sau admission). Không sửa output, gold hoặc số macro lịch sử; [retrieval-metric-erratum.json](retrieval-metric-erratum.json) bind source checksum và ghi cách tính. Đây là kiểm toán diễn giải offline, không chạy lại benchmark/model.
- [Deterministic/mock report](../../evaluation/agentic-rag-legal-answer-hotfix/README.md) chỉ kiểm tra contract, không chứng minh chất lượng model.
- L03 live NOT RUN; coverage nguồn một phần; câu trả lời có thể chưa hữu ích hoặc clarification không cần thiết. Chưa có thẩm định pháp lý độc lập; không xác nhận quyền lợi cá nhân.
- Các report trước release giữ nguyên trạng thái/identity tại thời điểm chạy, kể cả quyết định chưa deploy trước khi có phê duyệt cuối. Quyết định phát hành mới nằm ở report này, không sửa evidence cũ để giả khớp.

## 7. Docs, diagram, findings và rollback

- README và tài liệu active được đồng bộ riêng sau deploy; không redeploy chỉ vì commit tài liệu.
- Diagram Design giữ revision upstream đã ghim và cặp source HTML/SVG của PR #13. Không có thay đổi topology/semantics do chuyển từ candidate sang deployed; 6/6 sơ đồ hiện hành self-check/geometry đạt. Không regenerate diagram chỉ để đổi SHA.
- **P0:** không phát hiện trong phạm vi kiểm tra deployment/security public nêu trên; không tuyên bố đã kiểm tra mọi tình huống.
- **P1 còn lại:** false abstention/T01 usefulness; T02/L02/L03 legal-quality chưa xác nhận; helper pilot có flat reservation chưa chứng minh upper bound; nguồn chỉ review một phần. Không được dùng các giới hạn này để quảng bá tư vấn pháp lý đã kiểm định.
- Cold start/provider Free limits và kiểm tra mobile chỉ là emulation, chưa kiểm tra thiết bị thật/screen reader.
- Rollback ứng dụng đã biết hoạt động: **`b1c10f4bad6b89f1d555eb08f5216b4b285be6d6`**, Pages `636baf63-fde3-44c6-a26f-91f62d8cf970`, Render `dep-dbd26u2vcj2c739dtck0`. Redeploy SHA này bằng workflow hiện có cho cả hai dịch vụ, giữ `agentic_rag`, nguyên DB/corpus/policy; không restore/drop DB. Không cần rollback trong release này.

## 8. Evidence

- [public-metadata.json](public-metadata.json): management API allow-list, actual public health/source/fingerprint/bundle/security checks; không chứa secret.
- [browser-zero-groq.json](browser-zero-groq.json): kiểm tra browser bổ sung; history/citation seed được ghi nhãn rõ.
- [workflow-navigation.json](workflow-navigation.json): output gốc navigation/fingerprint sau deploy.
- [render-deploy.jsonl](render-deploy.jsonl): receipt gốc chỉ của deployment SHA release này.
- [merge-ci.json](merge-ci.json), [deploy-workflow.json](deploy-workflow.json): trạng thái job/step từ GitHub Actions.
- [SHA256SUMS](SHA256SUMS): checksum các evidence trên. Ảnh browser của workflow có trong artifact `deployment-evidence` tại run triển khai.

Artifact upload của workflow còn chứa một số report `deployment-chat`/receipt cũ vốn đã tracked trong source. **Không** tính chúng là chat test hay usage của release này; chỉ receipt đúng source SHA và navigation timestamp mới được dùng ở đây.
