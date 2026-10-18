# ADR 0001: Một pipeline và contract embedding cố định

**Trạng thái:** Chấp nhận

## Bối cảnh

Hệ thống cần truy xuất và đối chiếu quy định tiếng Việt trong giới hạn tài nguyên của hosting Free. Viện dẫn chính xác, cách diễn đạt tự nhiên và chi phí vận hành đều ảnh hưởng tới lựa chọn retrieval và model.

## Quyết định

Sử dụng một pipeline Agentic RAG với Groq GPT-OSS 120B. Query và corpus dùng E5 ONNX Q8 384 chiều, contract `multilingual-e5-small-onnx-q8-window-v1` và preprocessing đã ghim. Hybrid retrieval kết hợp từ khóa, vector, tiêu đề và viện dẫn bằng RRF.

SQLite phục vụ local; PostgreSQL/pgvector phục vụ deployment. Giữ embedding của các chunk không thay đổi khi thu gọn corpus.

## Phương án không chọn

Không thêm pipeline baseline, reranker, fine-tuning hoặc multi-agent trong phạm vi hiện tại. Việc bổ sung các thành phần này cần bài toán, bằng chứng đánh giá và ngân sách vận hành riêng; không được suy ra hiệu quả tốt hơn khi chưa so sánh cùng điều kiện.

## Hệ quả

- Contract embedding phải được kiểm tra khi ingest, restore và truy vấn; thay đổi model hoặc preprocessing cần kế hoạch chuyển đổi corpus.
- Một pipeline giảm số cấu hình cần vận hành và đánh giá, nhưng không loại bỏ hạn chế retrieval hoặc verifier.
- Hai backend lexical khác nhau có thể cho kết quả khác nhau; storage backend tham gia fingerprint và được công bố trong báo cáo.
- Runtime không thực hiện OCR hoặc chạy model sinh tại Render.

## Kiểm chứng

Kiểm tra model checksum, số chiều và contract; chạy regression retrieval/agent cùng các phép đo đã định nghĩa trong [đánh giá](../EVALUATION.md). Không thay model hoặc tăng ngân sách workflow chỉ để cải thiện benchmark.
