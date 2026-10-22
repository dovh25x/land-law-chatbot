# Demo evaluation v1 — 22/10/2026

- Suite khóa: `data/evaluation/demo-v1-20261022/` (12 ca, SHA256 `1423aa3023d3079bea32c6fa16d13448fd69f15eea14d97897ccb315d8e97c3d`).
- Ứng dụng được đo: commit `a1144d09c43d3427306cebd44c82e1189eb7fee4`.
- Corpus: `corpus-1afca764aa6692e0`.
- Policy nguồn: v2 candidate SHA256 `7e6ec4c4f581c9e8e7355288f7f76e61f67bdaed67d95f68d7d541c5b256983d`.

## Preflight ngày 22/10/2026

`preflight.json` ghi kết quả:

- Xã giao: 4/4 đạt; không retrieval, không citation, không gọi model.
- An toàn tất định: 3/3 đạt (phạm vi/hiệu lực, adverse review, citation integrity).
- Pháp luật: 5/5 truy xuất được chứng cứ đã review.
- Request Groq: 0; token: 0. Cả 5 ca pháp luật giữ `NOT RUN`.

## Trạng thái

Chưa chấm chất lượng câu trả lời pháp luật. Lần chạy thật cần phê duyệt riêng 5 request/15.000 token, tuần tự, không retry/repair. Không dùng preflight hoặc fixture thay cho kết quả live; không tuyên bố đây là thẩm định pháp lý.
