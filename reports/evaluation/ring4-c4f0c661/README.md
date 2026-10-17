# Đánh giá trên corpus Vành đai 4

Các artifact ở đây dùng corpus `corpus-581da76c79b0b362`, Groq GPT-OSS 120B và fingerprint `c4f0c661af82ab60cc9f918a89e7b417981b070268d2bddfee12116a003c7b25`. Backend đánh giá là SQLite qua operator CLI. PostgreSQL của dịch vụ có fingerprint khác; kết quả này không thay cho đánh giá retrieval hoặc latency trên deployment.

- [Bộ chính](smoke/results.md), [bốn regression probes](supplemental/results.md) và [bộ tự nhiên](natural/results.md) được chạy riêng, mỗi ca một attempt trên cấu hình này. Các retry HTTP trong lượt được tính trong số lần gọi LLM.
- `evaluation.json` chứa kết quả đầy đủ; `reviews.json` gắn checksum của đúng đáp án; `attempts.json` giữ các attempt. Review do Codex hỗ trợ đối chiếu tiêu chí khóa và nguồn, không phải thẩm định pháp lý độc lập.
- [Recall@8](retrieval/) đo hybrid search bằng câu hỏi gốc, không generation, không history rewriting hoặc evidence sau agent routing. Gold của N03 chứa cả parent và child trong khi search ưu tiên child: giữ nguyên annotation đã khóa và công khai giới hạn này.
- [Faithfulness mẫu](faithfulness.json) là chấm riêng trên đáp án cuối và context thực tế, cùng model với hệ thống. Xem coverage, ca không áp dụng và lỗi judge trước khi đọc tỷ lệ; citation khớp không chứng minh entailment.

S06, X02, X03, N02 và N04 chưa trả lời được nội dung cần thiết. Chặn diễn giải chưa được hỗ trợ giúp tránh lỗi nội dung đã biết nhưng không được tính thành task success. Bộ tự nhiên chưa đạt điều kiện tối thiểu năm trong sáu câu nội dung; không công bố rằng hệ thống đã hoàn tất tiêu chí chất lượng đó.

Các báo cáo fingerprint cũ vẫn được giữ riêng. Asset corpus đa dự án trước đó đã bị thu hồi; xem [bản ghi thu hồi](../../corpus-retirement.json). Không sửa checksum lịch sử hoặc ghép kết quả từ các fingerprint khác nhau.

Judge đánh dấu một lời giới hạn về danh mục/việc mở điều khoản trong S08 là chưa có bằng chứng trực tiếp. Đây có thể là giới hạn của cách tách claim cho phần mô tả quy trình; giữ nguyên verdict và điểm, không chấm lại để tăng tỷ lệ.
