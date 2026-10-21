# S06 — attempt cuối, 20/10/2026

**FAIL. Dừng tối ưu F03; không sửa hoặc chạy lại.**

- 1 attempt trên SQLite tạm riêng, Groq `openai/gpt-oss-120b`.
- 2 HTTP 200 requests: Draft và một repair trong cùng lượt; không transport retry, không LLM verifier request.
- Agent latency 5.815 giây; 6.115 prompt tokens + 1.989 completion tokens = 8.104 total tokens theo usage Groq.
- Runtime fingerprint: `2dab4dde69323ce35e9732748df40ce15c371d6380d694137a65faf05eccc179`.
- Corpus `corpus-a26bc99e541fbbe2`, câu hỏi/as_of S06 khóa `2024-08-02`.
- Kết quả `insufficient_evidence`: 0 verified claims, 0 citations phát hành.
- Protected runtime/tests/evaluation/snapshot không đổi trước/sau. Không thay production database/cloud/deployment.

## Đối chiếu kết quả

[Điều 95, bản Công báo chính thức](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/31-2024-qh15_2.pdf#page=5), trang PDF 5–7: khoản 1 xác định nhóm đối tượng; khoản 2 đặt các điều kiện thay thế cho các trường hợp thuộc khoản 1.

Draft đầu vẫn bỏ prerequisite khoản 1. Repair có cải thiện: nêu nhánh hộ gia đình/cá nhân không thuê đất trả tiền hằng năm ở khoản 1, rồi gắn các điều kiện thay thế ở khoản 2 với đối tượng này, giữ OR. Tuy nhiên structural guard vẫn từ chối vì diễn đạt này không khớp mẫu từ khóa phạm vi trong cửa sổ 80 ký tự quanh tham chiếu khoản 1. Đây là dấu hiệu false positive ở guard; không nên báo sai rằng repair hoàn toàn không nêu đối tượng.

Chưa qua LLM semantic/citation verification và không có claim/citation được phát hành. Vì vậy không đủ điều kiện pass. Raw drafts chỉ dùng chẩn đoán, không phải câu trả lời chatbot đã xác minh. Không chỉnh guard/prompt hoặc gọi model thêm.

## Artifact

- `runs/`: immutable attempt, records, structured outputs, metadata, summary theo harness hiện có. Giữ mẫu số suite 20 ca với đúng 1 ca được chạy.
- `retrieval/`, `wire/requests/`, `wire/responses/`: context công khai, request không có headers, status/usage/rate limits; không lưu hidden reasoning hoặc raw error body.
- `verification/`: verdict sau từng draft; `usage-events.json`: usage operator.
- `configuration-lock.json`, `protected-inputs-before.json`, `protected-inputs-after.json`, `execution-receipt.json`: nhận dạng và bảo toàn cấu hình.
- `reviews.json`: fail gắn answer checksum; `technical-review.json`: đối chiếu, tiêu chí, chẩn đoán và đề xuất Phase 2 chưa thực hiện.
- `execution-runner.py`: instrumentation quan sát, không đổi payload hoặc return value của runtime; `operator-cooldown.json`: cooldown quan sát được, không reset để chạy thêm.

Phase 2 chỉ đề xuất: kiểm soát nguồn pháp luật/receipts; xác minh deployment và backup/restore; khóa cấu hình và chuẩn bị evaluation tái lập. Giữ S06 fail là hạn chế đã biết. Chưa triển khai Phase 2, commit, push hoặc deploy.
