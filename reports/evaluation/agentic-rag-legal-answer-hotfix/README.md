# Agentic RAG legal-answer grounding hotfix — deterministic evidence

- **Ngày chạy:** 22/10/2026
- **Trạng thái:** bằng chứng regression tất định trên application contract; **không phải** kết quả Groq, benchmark chất lượng pháp lý hay nghiệm thu production.
- **Quyết định:** chỉ đủ điều kiện mở PR/review. Chưa deploy, chưa dùng thêm quota Groq, chưa thay corpus/policy/DB.
- **Production:** vẫn ở `b1c10f4bad6b89f1d555eb08f5216b4b285be6d6`. Hotfix chỉ được coi là release candidate sau khi có phê duyệt ngân sách và kết quả live riêng.

## 1. Phiên bản và nguồn gốc

| Thành phần | Giá trị |
|---|---|
| Baseline code | `982aae704d57127d4544d048c24aa295da40ff12` (`main`) |
| Production runtime | `b1c10f4bad6b89f1d555eb08f5216b4b285be6d6`; các file runtime liên quan trong báo cáo không khác `982aae7` |
| Candidate runtime | `d7e2fe59b672` — `fix(agentic): ground legal answers and claim-aware fallbacks` |
| Candidate tests | `tests/test_legal_answer_hotfix.py` trên branch cuối: 18 test; hai test coverage/classification suggestion được thêm sau commit runtime và không đổi runtime |
| Fixture | `tests/fixtures/legal-answer-hotfix-release.json`; 6 tài liệu, 31 chunk chọn lọc |
| Fixture SHA-256 | `1bbab6bb5f8ac9a2e90738fbe2c5abda025fa3fa5d42b83230c6f9251d4e5c08` |
| Fixture snapshot | `corpus-1afca764aa6692e0`; provenance ghi rõ đây là fixture regression, không phải production release |
| Corpus production | `corpus-1afca764aa6692e0`; policy standing v2 SHA `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d` |

Candidate commit `d7e2fe5` chứa runtime và 16 test. Branch cuối thêm hai test coverage/classification suggestion (tổng 18) và các thay đổi frontend/tài liệu/diagram; test thêm không thay đổi runtime. Không có thay đổi model, embedding, corpus, receipt, policy, migration hay production database trong đợt này.

## 2. Lỗi được tái hiện

Baseline `982aae7` (cùng hành vi runtime với production `b1c10f4` đối với các file liên quan):

1. **Citation guard toàn cục, không claim-aware.** `valid = bool(cited)` khiến một câu trả lời chỉ hỏi làm rõ bị coi là invalid. Fallback sau đó đổ tối đa hai trích đoạn nguyên văn vào câu trả lời.
2. **Marker nhóm không được nhận.** `[S1, S2]` không tạo ra marker hợp lệ, nên draft đúng nguồn vẫn bị đưa vào fallback.
3. **Thứ tự evidence chưa ưu tiên nguồn trực tiếp.** Với L01, baseline chọn `31/2024/QH15 — Điều 109` (hỗ trợ đào tạo, chuyển đổi nghề) thay vì quy định bồi thường/tái định cư trực tiếp của Hà Nội.
4. **Fallback dài, giống một câu trả lời.** Các fallback baseline dài 1.407–1.503 ký tự, có hai bullet trích đoạn và một câu hỏi chung; người dùng khó phân biệt đâu là kết luận, đâu là trích dẫn thô.

Hotfix sửa bốn điểm này ở lớp ứng dụng, không thay đổi kiến trúc:

- `legal_text.validate_answer_result()` kiểm tra theo từng câu; chỉ câu khẳng định pháp lý cần marker, câu hỏi làm rõ được phép không marker.
- Chấp nhận marker nhóm `[S1, S2]`, `[S1; S2]` và full-width; ID ngoài source map bị từ chối.
- `_admit()` xếp nguồn legal trực tiếp trước nghị quyết chuyển tiếp/context; giữ tối đa một context khi có legal, ưu tiên locator khác nhau, và giữ nguyên thứ tự search nếu câu hỏi trực tiếp về cơ chế chuyển tiếp/Nghị quyết 254/2025.
- Fallback chỉ nêu tối đa hai danh tính nguồn và tối đa một câu hỏi; không đổ excerpt. Clarification thuần được phát hành với citations rỗng và `support_level=insufficient`.

## 3. Phương pháp tất định

Runner dùng cùng fixture, cùng 10 scenario, cùng mock provider cho baseline và candidate. Provider giả lập trả một tool call cố định và một `SimpleAnswer` cố định; không gọi Groq, không gọi mạng, không dùng real model. Vì vậy kết quả đo **contract của ứng dụng**, không đo chất lượng sinh văn bản của model.

- Mỗi scenario chạy `BoundedAgenticRAG.run()` trên SQLite tạm và fixture đã publish.
- Tool execution được mock; retrieval/admission/validation/fallback là code thật.
- Không hardcode đáp án trong runtime; draft cố định chỉ là input để so sánh baseline và candidate.
- Định nghĩa scenario đã đóng băng tại [`scenarios.json`](scenarios.json); kết quả thô tại [`baseline-982aae7.json`](baseline-982aae7.json) và [`candidate-d7e2fe5.json`](candidate-d7e2fe5.json).

## 4. Kết quả 10 scenario

`llm_calls` và `tool_calls` là số đo của ứng dụng, không phải số request thật tới Groq.

| ID | Baseline `982aae7` | Candidate `d7e2fe5` | Kết quả đo |
|---|---|---|---|
| T01 | `answered`, partial, 1 citation `88/2024/NĐ-CP — Điều 24` | `answered`, partial, cùng citation | Không regression; bỏ câu hỏi làm rõ bị lặp ở cuối |
| T02 | `answered`, full, `88/2024/NĐ-CP — Điều 5` | `answered`, full, cùng citation | Không regression |
| L01 | `answered`, full, `31/2024/QH15 — Điều 109` | `answered`, full, `40/2026/QĐ-UBND — Điều 4` | Chọn đúng nguồn trực tiếp hơn; baseline chọn điều hỗ trợ nghề, không phải quy định bồi thường đất ở đang hỏi |
| L02 | `clarification_needed`, 2 excerpt, `254/2025/QH15 — Điều 3` + `31/2024/QH15 — Điều 111` | `answered`, full, `31/2024/QH15 — Điều 111` + `40/2026/QĐ-UBND — Điều 21` | Marker nhóm được nhận; draft đúng nguồn không còn bị fallback |
| L03 | `answered`, full, `88/2024/NĐ-CP — Điều 19` | `answered`, full, cùng citation | Không regression |
| T01-CLARIFY | `clarification_needed`, 2 excerpt, 2 citations | `clarification_needed`, 0 citation, câu hỏi thuần | Claim-free clarification hợp lệ; không còn trích đoạn thô |
| T02-CLARIFY | `clarification_needed`, 2 excerpt, 2 citations | `clarification_needed`, 0 citation, câu hỏi thuần | Claim-free clarification hợp lệ; không còn trích đoạn thô |
| UNCITED | `clarification_needed`, 2 excerpt, 2 citations | clarification ngắn, `missing_required_citation`, 2 citations danh tính nguồn | Claim không marker vẫn bị từ chối; fallback không đổ excerpt |
| GROUPED | `clarification_needed`, 2 excerpt, 2 citations | `answered`, `grounded_answer`, 2 citations | `[S1, S3]` được nhận và validate |
| UNKNOWN | `clarification_needed`, 2 excerpt, 2 citations | clarification ngắn, `unknown_citation_id`, 1 citation | `S9` không được phát hành; chỉ nguồn hợp lệ còn lại được nêu |

Tổng hợp:

- **6/10** scenario thoát khỏi fallback trích đoạn: L02, T01-CLARIFY, T02-CLARIFY, UNCITED, GROUPED, UNKNOWN. Trong đó L02/GROUPED chuyển sang `answered`; T01-CLARIFY/T02-CLARIFY thành clarification thuần; UNCITED/UNKNOWN thành fallback ngắn.
- **1/10** L01 vẫn `answered` nhưng chọn nguồn trực tiếp hơn (`40/2026/QĐ-UBND — Điều 4` thay vì `31/2024/QH15 — Điều 109`).
- **3/10** giữ nguyên trạng thái và citation: T01, T02, L03.
- **0** fallback candidate chứa bullet trích đoạn nguyên văn; baseline có **12** bullet trích đoạn trên 6 fallback.
- Candidate không phát hành marker `S9`; fallback UNKNOWN chỉ còn `88/2024/NĐ-CP — Điều 5`.

### Fallback trước/sau

| Scenario | Baseline: ký tự / excerpt | Candidate: ký tự / excerpt |
|---|---:|---:|
| L02 | 1.460 / 2 | 193 / 0 (đã answered) |
| T01-CLARIFY | 1.461 / 2 | 68 / 0 |
| T02-CLARIFY | 1.407 / 2 | 29 / 0 |
| UNCITED | 1.503 / 2 | 294 / 0 |
| GROUPED | 1.460 / 2 | 90 / 0 (đã answered) |
| UNKNOWN | 1.460 / 2 | 253 / 0 |

Đây là thay đổi về hình thức và an toàn của fallback, không chứng minh nội dung pháp lý của câu trả lời là đúng. Citation candidate vẫn chỉ là danh tính nguồn đã đối chiếu; không phải kết luận quyền lợi.

## 5. Validation reason codes và budget

Candidate trace ghi reason code rút gọn, không ghi draft/excerpt/nội dung hội thoại:

| Reason code | Số scenario |
|---|---:|
| `grounded_answer` | 6 (T01, T02, L01, L02, L03, GROUPED) |
| `legitimate_clarification` | 2 (T01-CLARIFY, T02-CLARIFY) |
| `missing_required_citation` | 1 (UNCITED) |
| `unknown_citation_id` | 1 (UNKNOWN) |

Budget trong cả 10 scenario:

- `llm_calls=2` cho mọi scenario (một tool decision + một final generation).
- `tool_calls=1` cho mọi scenario; không có tool-decision thứ hai.
- Không có repair loop; hard ceiling 3 request không bị chạm.
- Deadline 90 giây không được đo vì provider mock hoàn tất tức thời. Đây không phải bằng chứng latency.

## 6. Retrieval hậu hotfix — offline, zero quota

Hotfix có thay đổi thứ tự chọn evidence sau admission (`direct-first`, locator khác nhau, tối đa một context), nên benchmark retrieval được chạy lại dù corpus, gold, receipt, policy và embedding không đổi. Lệnh:

```bash
PYTHONPATH=backend .venv/bin/python scripts/evaluate_ring4_retrieval.py \
  --sqlite /tmp/opencode/legal-hotfix-retrieval.db \
  --output reports/evaluation/agentic-rag-legal-answer-hotfix/retrieval-post-hotfix.json
```

Cấu hình: corpus `corpus-1afca764aa6692e0`, policy standing v2 hiện hành, source review `reports/source-review-20261022/`, E5 ONNX Q8 `multilingual-e5-small-onnx-q8-window-v1`; 20/20 ca có gold. Kết quả:

| Chỉ số | Giá trị | Ghi chú |
|---|---:|---|
| Recall@5 | **0,975** | 39/40 gold chunk nằm trong top5; 20/20 ca có ít nhất một gold chunk |
| Admitted Evidence Recall@5 | **0,925** | 37/40 gold chunk vượt review + applicability; 20/20 ca có ít nhất một gold chunk admitted |
| Top-5 hit | **20/20** | mẫu số là 20 ca scored |
| Admitted top-5 hit | **20/20** | không có ca nào mất toàn bộ evidence liên quan |
| Gold chunk bị thiếu | S02: 1/1; N03: 1/2 | giữ nguyên gold đã khóa; không sửa annotation |

Output JSON của lần chạy này **byte-identical** với benchmark lịch sử `reports/qa/ring4-retrieval-offline-current.json` (SHA-256 `bcf5f7c7c73b0e0aee140628f1c5540c11421afbe8eb90457943af030a64ba11`). Vì vậy báo cáo **không** tuyên bố retrieval hay admission được cải thiện. Benchmark này đo top5 của store search và điều kiện admission; bước xếp hạng `direct-first` trong `_admit()` được kiểm tra riêng bằng scenario T01/L01 của runner tất định.

## 7. Kiểm thử đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `pytest -q tests/test_legal_answer_hotfix.py` | **18 passed** |
| Sáu file focused: hotfix, bounded Agentic RAG, source review, scoped gate, standing snapshot, conversation | **150 passed** |
| Toàn bộ backend | **653 passed** |
| Frontend unit | **30 passed** |
| Frontend build | pass |
| `npm audit --audit-level=high` | 0 vulnerability |
| Playwright desktop + mobile | **38 passed** |
| `scripts/check_secrets.py` | pass, không phát hiện secret/credential pattern |
| Diagram self-check (6 sơ đồ hiện hành) | 6/6 OK |
| Diagram geometry | 0 finding |
| SVG XML parse | 3/3 file đã export parse thành công |

Các test hotfix dùng chính fixture này và không gọi Groq. Chúng bao phủ thêm T01/T02, social control, budget exhaustion, provider schema failure, grouped/unknown marker, claim-free clarification, source ordering và evidence coverage của ba câu hỏi pháp luật trên trang đầu. Ba câu này lần lượt lấy được `31/2024/QH15 — Điều 95`/`40/2026/QĐ-UBND — Điều 4`, `88/2024/NĐ-CP — Điều 19`/`31/2024/QH15 — Điều 109`, và `40/2026/QĐ-UBND — Điều 21`/`88/2024/NĐ-CP — Điều 24`/`31/2024/QH15 — Điều 111` trong fixture đã review. Đây là kiểm tra coverage, không hardcode câu trả lời.

## 8. Giới hạn và điều không được suy ra

- **Không có kết quả Groq/live.** Không được nói false abstention đã hết trên production, không được nói tỷ lệ trả lời đúng đã tăng.
- **Không có semantic legal judge.** Guard chỉ kiểm tra identity/citation/condition lexical; một paraphrase không nêu điều/khoản cụ thể vẫn có thể sai.
- **Fixture nhỏ, chọn lọc.** 6 tài liệu/31 chunk không đại diện cho toàn bộ corpus 60 tài liệu/7.396 chunk.
- **L03 live vẫn NOT RUN.** Baseline L03 trong báo cáo là deterministic fixture, không thay thế kết quả production.
- **`simple_rag` rollback không được sửa.** Rollback vẫn dùng hành vi citation/fallback cũ; không dùng rollback để đánh giá hotfix.
- **Không thay đổi production.** Báo cáo này không chứng minh deploy, migration, corpus release hoặc quyền lợi hộ dân.

## 9. Cách tái lập

Từ repo root, dùng runner đã đóng băng trong báo cáo:

```bash
# Baseline: dùng backend của worktree baseline.
git worktree add /tmp/opencode/legal-hotfix-baseline 982aae704d57127d4544d048c24aa295da40ff12
PYTHONPATH=/tmp/opencode/legal-hotfix-baseline/backend .venv/bin/python \
  reports/evaluation/agentic-rag-legal-answer-hotfix/run_scenarios.py \
  /tmp/opencode/legal-hotfix-baseline-rerun.json

# Candidate: dùng backend hiện tại.
PYTHONPATH=backend .venv/bin/python \
  reports/evaluation/agentic-rag-legal-answer-hotfix/run_scenarios.py \
  /tmp/opencode/legal-hotfix-candidate-rerun.json
```

Runner dùng mock provider, không gọi Groq. Định nghĩa scenario và input mock nằm tại [`scenarios.json`](scenarios.json). Test tất định tương ứng nằm tại [`tests/test_legal_answer_hotfix.py`](../../../tests/test_legal_answer_hotfix.py); fixture provenance nằm trong [`tests/fixtures/legal-answer-hotfix-release.json`](../../../tests/fixtures/legal-answer-hotfix-release.json). Runner đã được chạy lại trên candidate và cho output giống byte-for-byte với `candidate-d7e2fe5.json`.

## 10. Artifact và checksum

| File | SHA-256 |
|---|---|
| [`baseline-982aae7.json`](baseline-982aae7.json) | `398df6d4d0907124afc2538a741bc473211251ce4c654ff8c5399937fdbd82da` |
| [`candidate-d7e2fe5.json`](candidate-d7e2fe5.json) | `0aed7aec39cf5494a8c5a75b2477ebe7e23ed27cda69196528b2a4401f1e98c3` |
| [`scenarios.json`](scenarios.json) | `d637c85f690650fa145a246c2d8bb9122c912cdec06366c43bc4914bea6fc73f` |
| [`retrieval-post-hotfix.json`](retrieval-post-hotfix.json) | `bcf5f7c7c73b0e0aee140628f1c5540c11421afbe8eb90457943af030a64ba11` |
| [`run_scenarios.py`](run_scenarios.py) | `5640a08d0fd661612ce94c59e1ed1bd37535c69872afd30d01510c4179e38fbb` |
| Fixture | `1bbab6bb5f8ac9a2e90738fbe2c5abda025fa3fa5d42b83230c6f9251d4e5c08` |

Các file JSON là output thô của runner; không chỉnh sửa để khớp kết luận. Báo cáo release trước vẫn giữ nguyên tại [`../agentic-rag-final/FINAL_RESULT.md`](../agentic-rag-final/FINAL_RESULT.md) và không bị dùng thay cho bằng chứng hotfix này.
