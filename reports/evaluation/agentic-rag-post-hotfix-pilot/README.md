# Post-hotfix Agentic RAG pilot — một phần

- **Ngày chạy:** 22/10/2026
- **Trạng thái:** **PARTIAL** — 2/4 case hoàn tất; T02 bị chặn trước provider, L02 chưa chạy.
- **Phạm vi:** một lần chạy thật, tuần tự, đã được phê duyệt trước; không retry/repair.
- **Production:** vẫn ở `b1c10f4bad6b89f1d555eb08f5216b4b285be6d6`; **chưa deploy**.
- **Runtime candidate:** `d7e2fe59b672`; branch head lúc chạy: `76e42e6877262bc6bfd63a81a57040c2bef98e77`.

## 1. Phê duyệt và cấu hình

Đã được phê duyệt: A01, T01, T02 (follow-up), L02; tối đa **10 request / 30.000 token reserved**, 3.000 token/request, tuần tự, cooldown 20 giây, không retry/repair, dừng khi lỗi hoặc vượt ngân sách.

| Thành phần | Giá trị |
|---|---|
| Suite | `agentic-v1-20261022`, SHA-256 `91cb76aefb292d8e426f4cc7e9433be5bcc8face35341e0b523a03a25acb7621` |
| Corpus | `corpus-1afca764aa6692e0` |
| Policy | standing v2, SHA `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`; 43 admitted passages |
| Model | `openai/gpt-oss-120b` |
| Embedding | `multilingual-e5-small-onnx-q8-window-v1` |
| Lưu trữ | SQLite tạm restore từ backup; không ghi production DB |
| T02 history | History đóng băng của suite, cùng session; **không** dùng output T01 thực |

Lệnh đã dùng:

```bash
PYTHONPATH=backend .venv/bin/python scripts/evaluate_agentic_pilot.py \
  --live --cases A01 T01 T02 L02 \
  --output reports/evaluation/agentic-rag-post-hotfix-pilot/live.json \
  --request-cap 10 --token-cap 30000 \
  --global-request-cap 10 --global-token-cap 30000 \
  --ledger reports/evaluation/agentic-rag-post-hotfix-pilot/request-budget.json \
  --ledger-identity agentic-rag-post-hotfix-pilot-20261022 \
  --cooldown-seconds 20
```

Không sửa frozen suite, gold label, policy, receipt, corpus, model hay embedding.

## 2. Kết quả

| Case | Trạng thái | Kết quả | Request Groq | Tool | Token | Latency |
|---|---|---|---:|---:|---:|---:|
| A01 | `answered` | **PASS** social, không citation/retrieval | 1 | 0 | 751 | 635 ms |
| T01 | `clarification_needed` | **PARTIAL** — clarification an toàn, chưa phải câu trả lời điều kiện đầy đủ | 2 | 1 | 3.987 | 17.361 ms |
| T02 | `error` / `BudgetExceeded` | **NOT RUN** — chặn trước request Groq | 0 | 0 | 0 | — |
| L02 | — | **NOT RUN** — chưa tới lượt | 0 | 0 | 0 | — |

### A01

- Trả lời giới thiệu năng lực, có “Vành đai 4”, không có “Điều ”/“Nghị định”, không citation, không retrieval.
- Đúng expected status; 1 request; 751 token.

### T01

- Trace báo draft bị guard từ chối vì `missing_required_citation` (3 claim, 1 claim chưa marker). Draft không được lưu, nên không review lại được nội dung bị loại.
- Bản phát hành là clarification ngắn, không đổ excerpt; nêu hai danh tính nguồn:
  - `40/2026/QĐ-UBND — Điều 21`
  - `31/2024/QH15 — Điều 111`
- Có câu hỏi xác minh “đã nhận quyết định thu hồi đất hoặc thông báo thu hồi chưa?”; không kết luận quyền lợi.
- 5 evidence admitted; 2 citation identity; 2 request; 1 tool; 1 embedding; 3.987 token.
- **Không** phải câu trả lời điều kiện đầy đủ; task success chỉ đạt PARTIAL và vẫn là false abstention theo rubric nội dung lịch sử (evidence liên quan đã có). Expected status cho phép clarification chỉ là kiểm tra cơ học, không phải gold cho task success.

### T02 và L02

- T02 dừng ở `BudgetExceeded` trước khi gọi provider; không có request, không có citation.
- Counter ứng dụng `llm_calls` của lượt lỗi không được runner lưu; không suy ra counter này bằng 0 từ số HTTP request bằng 0.
- L02 chưa chạy; **không** có kết luận false abstention cho L02.
- L03 live vẫn **NOT RUN**, ngoài phạm vi pilot này.

## 3. Metrics

| Chỉ số | Kết quả |
|---|---|
| Task Success | 1 full (A01), 1 partial (T01), 2 NOT RUN (T02, L02) |
| False Abstention | T01: **1/1 ca legal hoàn tất**; T02/L02 chưa có kết quả. Mẫu một ca, không ngoại suy tỷ lệ |
| Grounded Answer | **NOT MEASURED** — 0 câu trả lời pháp lý substantive; không tính clarification là faithfulness pass |
| Citation Correctness | 2/2 citation identity hợp lệ; T01 không dùng citation để chống đỡ claim nội dung |
| Tool selection | 2/2 decision đúng (A01 không tool; T01 chọn `search_legal_evidence`) |
| Tool execution | 1/1 thành công; không có tool thứ hai |
| Unsupported legal claims | 0 trong nội dung đã phát hành |
| Raw-excerpt fallback | 0 |
| Requests thực tế | 3 / 10 |
| Reserved tokens | 9.000 / 30.000 |
| Confirmed tokens | 4.738 |
| Provider errors | 0 HTTP 429/5xx/format |
| Internal budget stop | 1 |
| Median latency (2 case) | 8.998 ms |
| p95 mẫu nhỏ | 17.361 ms (giá trị lớn nhất) |

**Lý do dừng:** request cuối của T01 được provider báo 3.242 token, vượt reservation phẳng 3.000 token. `PilotAllocation` đặt `blocked_reason=single_request_exceeded_reservation` và chặn T02 trước khi gửi request. Đây là **budget guard nội bộ**, không phải lỗi Groq, không phải chạm trần 10 request/30.000 token. Đã giữ nguyên artifact; **không chạy lại**.

Reservation phẳng 3.000 không phải upper bound đã chứng minh: request đã vượt reservation trước khi guard có thể chặn lượt sau. Vì vậy pilot chưa đáp ứng yêu cầu kiểm chứng affordability theo từng request; không coi việc dừng này là bằng chứng reservation đủ an toàn cho lần chạy tiếp.

## 4. Đánh giá và giới hạn

- A01 đạt kiểm tra social; T01 chứng minh fallback mới không đổ trích đoạn và không phát hành claim thiếu citation, nhưng chưa chứng minh trả lời điều kiện đầy đủ.
- T01 vẫn false abstention; T02/L02 chưa chạy. Không thể kết luận hotfix đã xử lý xong vấn đề này.
- Không thể kết luận hotfix đạt release gate chỉ từ 2 case hoàn tất.
- Citation correctness ở đây là **identity/source admission**, không phải thẩm định pháp lý độc lập hay semantic entailment.
- Ledger pilot không lưu rate-limit header của provider, nên artifact này không chứng minh được hạn mức Free TPM/RPM còn lại; lần tiếp theo cần kiểm tra độc lập trước mỗi request.
- Mẫu nhỏ, một lần chạy; không dùng để suy ra chất lượng toàn bộ hoặc quyền lợi hộ dân.
- Không deploy, không đổi production DB/corpus/policy, không dùng `simple_rag` rollback để đánh giá hotfix.

## 5. Artifact và checksum

| File | SHA-256 |
|---|---|
| `live.json` | `1edab73afec8740526aaa9228572c98a34c8e8ab81dec41d0b5aab75a0b31b36` |
| `request-budget.json` | `9ce9d25b9c83f0efe4c7ce7cfda978a3f436900d26b3a88e5a764f32892e3d78` |
| `review.json` | `baf8a0affa275a35bea7841c82010108415de240cf19586739f6353f6aa8eff8` |

`live.json` là output thô của runner: hai kết quả hoàn tất (A01/T01) và một record lỗi (T02), không có output L02. `request-budget.json` là ledger của allocation. Review do assistant thực hiện, bind checksum của cả hai artifact; không phải thẩm định pháp lý độc lập. Không chỉnh sửa output thô hoặc ledger để khớp kết luận.

## 6. Bước tiếp theo

Không merge/deploy từ trạng thái PARTIAL. Nếu muốn hoàn tất pilot, cần phê duyệt **mới** cho một allocation riêng (không tự retry) với reservation/request phù hợp để chạy T02 và L02 trong giới hạn tổng được duyệt. Sau đó mới review lại và xin phê duyệt release.
