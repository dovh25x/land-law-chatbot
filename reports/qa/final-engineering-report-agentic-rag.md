# Báo cáo kỹ thuật cuối — Bounded Agentic RAG và chất lượng corpus Ring Road 4

- **Ngày:** 22/10/2026
- **Nhánh:** `mvp/final-optimization`
- **PR:** [#11](https://github.com/dovh25x/land-law-chatbot/pull/11)
- **Production hiện hành:** runtime `625e90e84079950e953267d1e4caaf0cb3e8c8e5`, `EXECUTION_MODE=simple_rag`
- **Trạng thái đợt này:** code + test + audit hoàn tất trên local; **chưa deploy, chưa chạy Groq mới, chưa đổi corpus/policy production**.
- **Commit workstream:** `e203af9` (guard citation/điều kiện), `6470761` (agentic runtime), `5d0f340` (retrieval admitted + audit), `85f504d` (khóa pilot + báo cáo).
- **CI:** run `39781150352` tại `85f504d` — backend, frontend, image **success**.
- **Bằng chứng chi tiết:** `reports/qa/`.

## 1. Nguyên nhân thật của lỗi hội thoại quy hoạch/tái định cư

Đã tái hiện offline đúng hai lượt:

1. “Tôi có được bố trí chỗ ở mới nếu nhà hiện tại đang ở diện quy hoạch không?”
2. “đất tôi ở thuộc dự án Vành đai 4”

**Kết quả trước sửa:** cả hai lượt có 8/8 ứng viên top-8 ở trạng thái gate `unknown` (tài liệu chưa có receipt), nên `SimpleRAG` loại toàn bộ trước khi gọi model và trả `insufficient_evidence`. Đây là lỗi **top-K crowding + admission fail-closed**, không phải model bịa hay citation validation.

Các nguyên nhân phụ:

- Truy vấn lượt 2 không kế thừa chủ thể vì `_retrieval_query` chỉ mở rộng với một số mẫu mở đầu; câu “đất tôi ở…” không khớp.
- `luat-nha-o-2023` Điều 72 (bố trí nhà ở tái định cư/chỗ ở tạm thời) rất liên quan nhưng chưa có receipt.
- 5 văn bản dự án Vành đai 4 (1 quyết định + 4 tin chính thức) chưa được review; chúng chỉ có thể là context, không được chứng minh quyền lợi.
- Một số điều Luật Đất đai (Điều 94/104/107/108) chỉ nằm trong cửa sổ lịch sử đã hết hạn của receipt cũ.

**Sau sửa:** cả hai lượt có 8/8 ứng viên top-8 là đoạn đã review/admitted, gồm Điều 95, Điều 111, Điều 17/21 QĐ 40/2026, NĐ 88/2024 và NQ 254/2025. Chi tiết từng candidate, score, gate, applicability và excerpt nằm tại `reports/qa/phase-a-two-turn-diagnosis.json`.

## 2. Bounded Agentic RAG

- Mode mới `agentic_rag` trong `backend/landlaw/agentic_rag.py`; `simple_rag` giữ làm rollback.
- Model dùng Groq native tool calling với hai tool đọc-only:
  - `search_legal_evidence(query, topic?)`
  - `open_legal_provision(document_id, locator, query?)`
- Ứng dụng kiểm tra mọi tham số tool; model không có quyền SQL, ghi dữ liệu, đọc file, mở URL tùy ý hay dùng credential.
- Giới hạn: tối đa **3 request Groq/lượt**, tối đa **2 tool execution**, tuần tự, không repair loop.
- Groq không hỗ trợ đồng thời strict Structured Outputs và tool use: request chọn tool gửi `tools` + `tool_choice="auto"`, request trả lời cuối gửi JSON schema nghiêm ngặt.
- Hội thoại: model thấy history giới hạn; fallback `conversation.contextual_retrieval_query` xử lý các tiếp nối rõ (`vậy`, `còn`, `thế`, `nhưng`, `đất tôi`, `nhà tôi`). Lượt xã giao trả lời trực tiếp bằng model, không dùng template cố định.
- Nếu model cố trả lời pháp luật trực tiếp mà không gọi tool, ứng dụng bắt buộc retrieval và sinh câu trả lời cuối có nguồn.
- Nếu không có evidence, trả về một câu hỏi làm rõ đúng trọng tâm (quyết định thu hồi/loại đất/giấy tờ) thay vì câu “Chưa đủ căn cứ” chung chung.

Tài liệu implementation: `docs/AGENTIC_RAG.md`.

## 3. Sửa lỗi chất lượng L01/L02/L03/L05

- **L01/L02:** thêm guard xác định danh tính điều/khoản/số hiệu văn bản theo từng câu và từng citation; chặn điều kiện thủ tục thêm vào không có trong đoạn được dẫn (`phương án`, `phê duyệt`, `giấy chứng nhận`, `cư trú`, `vi phạm`, ...); prompt tách bạch điều kiện bồi thường / hình thức bồi thường / hỗ trợ / tái định cư / thủ tục.
- **L03:** số hiệu văn bản trong câu trả lời phải khớp `document_number` của chính nguồn được dẫn, không chỉ xuất hiện ở đâu đó trong đoạn.
- **L05:** evaluator dùng kiểm tra phủ định; “chưa thể xác nhận … đủ chắc chắn” không còn bị coi là khẳng định “chắc chắn”. Kết quả lịch sử được giữ nguyên, không sửa điểm cũ.
- Thêm guard **nguồn bối cảnh/dự án không chứng minh quyền lợi**: tin dự án và quyết định chủ trương không được dùng cho câu khẳng định hộ được bồi thường/tái định cư.
- Deterministic guard là bộ lọc loại bỏ, **không thay thế thẩm định pháp lý độc lập**.

## 4. Corpus: số liệu và kết luận

| Lớp | Số liệu |
|---|---|
| `data/sources.json` | 71 bản ghi; 60 verified, 11 pending |
| Release đang phục vụ | `corpus-1afca764aa6692e0`: 60 tài liệu, 7.396 chunk/embedding |
| Tài liệu có receipt đang pin | 10 |
| Đoạn đã review | 74 |
| Đoạn admitted ngày 22/10/2026 | 43 (42 standing + 1 legal window) |
| Phân loại A/B/C/D/E/F | 8 / 1 / 4 / 12 / 0 / 35 |
| Tài liệu dự án | 5 (1 quyết định + 4 tin), chưa có receipt |
| Công văn/tài liệu không liên quan trong release | 0 (10 bản songhong/olympic đã retired từ trước, ngoài release) |

**Vì sao nhiều chunk nhưng ít admitted:** release chứa toàn bộ văn bản để tra cứu, nhưng chỉ đoạn có receipt và `verified_scope` mới được dùng làm căn cứ; 50/60 tài liệu chưa có receipt, và 31 đoạn reviewed chỉ thuộc cửa sổ lịch sử không phủ 22/10/2026. Đây là fail-closed theo thiết kế, không phải lỗi index.

Các khoảng trống ưu tiên: Luật Nhà ở 2023 Điều 72; Luật Đất đai các điều 94/104/107/108; NĐ 88/2024 Điều 19/30/31; Luật Quy hoạch 2025; nhóm khiếu nại; nguồn vận hành Hà Nội. Kế hoạch review chi tiết: `reports/qa/ring4-source-review-plan.md`. Đợt này **không thêm, không xóa, không tạo receipt** và giữ nguyên 43 đoạn admitted.

## 5. Thay đổi retrieval

- Thêm scope admitted cho từng release/ngày và nhánh retrieval riêng: đoạn đã review được “cứu” nếu các nhánh thường bỏ sót, nhưng không xáo trộn các hit mạnh đã có.
- Kết quả gold offline 20 ca (smoke/supplemental/natural): Recall@5 **0,975**, admitted Recall@5 **0,925** — bằng baseline, đồng thời hai lượt hội thoại từ 0/8 lên 8/8 admitted.
- Chi tiết: `reports/qa/ring4-retrieval-offline-baseline.json` và `...-current.json`.

## 6. Kiểm thử

| Hạng mục | Kết quả |
|---|---|
| Backend `pytest -q` | **634 passed** |
| Frontend unit `npm test` | **29 passed** |
| Frontend build | **pass** |
| Playwright desktop/mobile | **36 passed** |
| Secrets scan | **pass** |
| Corpus audit `audit_corpus.py` | 60 documents, 7.396 chunks, 0 error, 0 warning |
| Citizen coverage audit | 12 requirements, `coverage_approved=false` |
| CI | run `39781150352` tại `85f504d` — backend, frontend, image **success** |

Test mới tiêu biểu: model chọn tool cho câu pháp luật; social trả lời trực tiếp; bắt buộc retrieval khi model trả lời pháp luật trực tiếp; cap 2 tool; sai điều/khoản/số hiệu văn bản bị loại; điều kiện thêm vào không nguồn bị loại; tin dự án không chứng minh quyền lợi; L05 không còn false positive.

## 7. Đánh giá thật (đề xuất, chưa chạy)

- Suite khóa: `data/evaluation/agentic-v1-20261022/`, SHA256 `91cb76aefb292d8e426f4cc7e9433be5bcc8face35341e0b523a03a25acb7621`.
- 9 ca: 1 social, 2 lượt hội thoại quy hoạch/tái định cư liên tiếp, L01, L02, L03, L04 control, 1 out-of-scope, 1 thiếu nguồn.
- Ngân sách hard cap đề xuất: **23 request / 69.000 token**, tuần tự, cooldown 20 giây, không retry/repair.
- Tier gọn hơn: A01 + T01 + T02 + L01 + L02 + L03 = tối đa **16 request / 48.000 token**.
- Trạng thái: `NOT RUN` — cần phê duyệt ngân sách Groq trước khi thực thi. Chi tiết rubric: `reports/qa/agentic-rag-pilot-proposal.md`.

## 8. Phát hành và rollback

- Runtime hiện tại vẫn là `625e90e` với `EXECUTION_MODE=simple_rag`; chưa deploy mode mới.
- Rollback mode mới: `EXECUTION_MODE=simple_rag` + redeploy SHA đã kiểm thử; corpus/policy không đổi.
- Corpus rollback: giữ policy v2 và release hiện hành; mọi candidate review mới phải tạo file riêng, không sửa release đang chạy.
- Sau khi được duyệt mới: chạy CI trên đúng SHA, deploy, bật `agentic_rag`, kiểm tra public E2E và quota.

## 9. Blocker và phê duyệt cần thiết

**P0 — claim chất lượng:** L01/L02/L03 đã có guard và regression test nhưng **chưa được xác nhận bằng model thật**. Không tuyên bố “legal quality passed” trước pilot.

**P1:**
- Thiếu review cho Luật Nhà ở Điều 72, Luật Quy hoạch 2025, nhóm khiếu nại và nguồn vận hành Hà Nội.
- Văn bản dự án chưa có receipt nên câu hỏi C09 chỉ có thể trả lời ở mức pháp luật chung + nêu khoảng trống.
- Chưa có thẩm định pháp lý độc lập.

**P2:** `/api/v1/evaluations/latest` production vẫn là báo cáo cũ 17/10/2026; mobile acceptance là emulated; chưa load-test quota.

**Cần phê duyệt:**
1. Ngân sách Groq cho pilot (Tier gọn hoặc full).
2. Review nguồn/tạo receipt + candidate policy mới trước khi kích hoạt.
3. Deploy production mode `agentic_rag` và chạy public E2E.

Không có secret, token hay nội dung hội thoại nào được ghi vào báo cáo này.
