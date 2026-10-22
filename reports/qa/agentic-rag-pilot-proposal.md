# Đề xuất pilot đánh giá Bounded Agentic RAG

- **Trạng thái:** `NOT RUN` / `CHỜ PHÊ DUYỆT NGÂN SÁCH GROQ`
- **Suite:** `data/evaluation/agentic-v1-20261022/` — frozen before generation
- **SHA256 scenarios:** `91cb76aefb292d8e426f4cc7e9433be5bcc8face35341e0b523a03a25acb7621`
- **Corpus:** `corpus-1afca764aa6692e0`
- **Policy:** `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`
- **Runtime dự kiến:** head agentic RAG sau khi CI xanh; chưa deploy production ở thời điểm đề xuất.

## 1. Vì sao cần pilot mới

Kết quả 4/5 task success, 3/5 grounded thuộc cấu hình **Simple RAG cũ** và
không thể dùng để kết luận cho pipeline có tool calling. Pipeline mới thực hiện
nhiều request hơn trên mỗi lượt pháp lý (quyết định tool + sinh câu trả lời),
nên phải đo lại số request, token, tool-selection và citation.

## 2. Bộ ca đã khóa

| ID | Loại | Nội dung | Trạng thái mong đợi | Request tối đa |
|---|---|---|---|---:|
| A01 | social | “Xin chào, bạn giúp được gì cho tôi?” | Trả lời trực tiếp, không retrieval | 1 |
| T01 | legal — lượt 1 | “Tôi có được bố trí chỗ ở mới nếu nhà hiện tại đang ở diện quy hoạch không?” | Trả lời có điều kiện hoặc hỏi đúng 1 câu | 3 |
| T02 | legal — lượt 2, có history | “đất tôi ở thuộc dự án Vành đai 4” | Hiểu ngữ cảnh, nêu thu hồi/bồi thường/tái định cư, không kết luận quyền lợi | 3 |
| L01 | legal | điều kiện bồi thường đất ở | Đúng Điều 95, không thêm điều kiện cư trú | 3 |
| L02 | legal | không có Giấy chứng nhận nhưng có quyết định giao đất | Đúng khoản 2 Điều 95, không thêm điều kiện | 3 |
| L03 | legal | hỗ trợ ổn định đời sống 12 tháng | Đúng QĐ 40/2026/QĐ-UBND, không gán NĐ 49 | 3 |
| L04 | legal — control | tái định cư tại phường | Giữ kết quả thành công trước đây | 3 |
| X01 | social/out-of-scope | “Bạn giúp tôi viết code Python nhé” | Từ chối lịch sự, không retrieval | 1 |
| X02 | missing source | thủ tục cấp Giấy chứng nhận lần đầu ở Hà Nội | Nêu khoảng trống nguồn, không bịa thủ tục | 3 |

## 3. Ngân sách đề xuất

- Request tối đa theo thiết kế: **23**.
- Token reserve mỗi request: **3.000** → hard cap **69.000 token**.
- Dự kiến thực tế: 14–20 request nếu model gọi một tool rồi sinh câu trả lời.
- Thực thi tuần tự, cooldown 20 giây giữa các ca, **không retry, không repair**.
- Mọi request được ghi ledger; ca vượt budget được giữ `NOT RUN`, không thay thế.
- Nếu muốn tiết kiệm hơn, có thể duyệt Tier 1 gồm A01, T01, T02, L01, L02, L03
  (tối đa 16 request / 48.000 token) và để L04, X01, X02 cho Tier 2.

## 4. Tiêu chí chấm

- **Tool selection:** social không gọi tool; câu pháp lý phải gọi tool trước khi khẳng định.
- **Follow-up:** T02 dùng đúng ngữ cảnh T01, không trả lời chung chung.
- **Task success:** trả lời đúng câu hỏi, có điều kiện khi thiếu dữ kiện.
- **Grounded:** mỗi câu pháp lý có citation đúng đoạn; không thêm điều kiện/điều khoản ngoài nguồn.
- **Citation correctness:** đúng văn bản, điều, khoản; L03 không gán sai nhãn.
- **Unsupported condition:** 0 lỗi kiểu “không vi phạm quy định về cư trú” hoặc điều kiện ngoài nguồn.
- **False abstention:** không từ chối khi có nguồn đủ để trả lời có điều kiện.
- **Provider failures:** ghi nhận riêng, không tính là task success.
- **Token/latency:** tổng token, token từng ca, thời gian end-to-end.

## 5. Điều kiện trước khi chạy

1. CI xanh trên đúng SHA agentic RAG.
2. Preflight offline xác nhận policy 43 đoạn, retrieval hai lượt T01/T02 có evidence.
3. Xác minh quota Groq Free và TPM/RPM thực tế.
4. Phê duyệt bằng văn bản của người dùng cho ngân sách hard cap.
5. Không dùng credit trả phí; không tự retry.

## 6. Kết quả offline hiện có (không Groq)

- Retrieval gold 20 ca (smoke/supplemental/natural): Recall@5 **0,975**, admitted Recall@5 **0,925**.
- Hai lượt hội thoại T01/T02 trong chẩn đoán offline: **8/8** ứng viên top-8 là đoạn đã review/admitted (trước khi sửa là **0/8**).
- Toàn bộ 630 test backend pass; chi tiết ở `reports/qa/`.
