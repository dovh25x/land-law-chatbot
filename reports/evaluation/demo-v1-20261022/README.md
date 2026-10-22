# Demo evaluation v1 — 22/10/2026

- Suite khóa: `data/evaluation/demo-v1-20261022/` (12 ca, SHA256 `1423aa3023d3079bea32c6fa16d13448fd69f15eea14d97897ccb315d8e97c3d`).
- Preflight: commit `625e90e`. Live: commit `1e1b470` (chênh lệch so với `625e90e` chỉ là báo cáo; runtime không đổi so với `a1144d0`).
- Corpus: `corpus-1afca764aa6692e0`.
- Policy nguồn: v2 candidate SHA256 `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`.

## Preflight ngày 22/10/2026

`preflight.json` ghi kết quả:

- Xã giao: 4/4 đạt; không retrieval, không citation, không gọi model.
- An toàn tất định: 3/3 đạt (phạm vi/hiệu lực, adverse review, citation integrity).
- Pháp luật: 5/5 truy xuất được chứng cứ đã review.
- Request Groq: 0; token: 0. Cả 5 ca pháp luật giữ `NOT RUN`.

## Attempt 1

Lần chạy live đầu tiên dừng do lỗi event loop sau một request đã xác nhận; không có file kết quả và không ca nào được tính là hoàn thành. Ledger và mô tả byte-exact nằm trong `attempts/`. Lỗi runner đã được sửa bằng một event loop cho cả 5 ca; allocation thay thế được phê duyệt riêng.

## Lần chạy thay thế

- 5/5 ca pháp luật chạy, 5 request, 10.442 token thực tế; không retry/repair.
- Auto-check: 4/5. L05 bị bắt nhầm vì regex `chắc chắn` gặp cụm phủ định "đủ chắc chắn".
- Đọc thủ công: **4/5 task success**, **3/5 grounded**, **0/5 false abstention**.
- L01: điều kiện thứ hai dẫn sai [S3]/[S5] và thêm điều kiện "không vi phạm cư trú" không có trong nguồn.
- L02: đúng hướng nhưng dẫn "khoản 1" thay vì khoản 2 và thêm điều kiện không có evidence.
- L03: đúng số liệu 12 tháng; phần Lưu ý nhầm nhãn Nghị định 49/QĐ40.
- L04, L05: đạt; L05 từ chối tính tiền chính xác và hỏi thêm dữ kiện.
- Raw: `live-20261022-replacement-live.json`. Bản review: `live-20261022-replacement-reviewed.json` (có `raw_artifact_sha256`). Ledger: `live-20261022-replacement-live-budget-ledger.json`.
- Tổng đã xác nhận qua hai lần: 12.767 token; attempt 1 còn một reservation 3.000 token không xác nhận response.

## Trạng thái

Live evaluation đã hoàn tất nhưng **không** chứng minh chất lượng pháp lý. Các lỗi L01/L02 là finding phải xử lý trước khi tuyên bố faithfulness/legal quality; L03 cần sửa nhãn nguồn. Không dùng preflight hoặc fixture thay cho kết quả live; không tuyên bố đây là thẩm định pháp lý độc lập.
