# Pipeline và embedding

Trạng thái: chấp nhận.

## Quyết định

Giữ một Agentic RAG, Groq GPT-OSS 120B và E5 ONNX Q8 384 chiều cùng preprocessing đã ghim.

## Lý do và hệ quả

Hybrid retrieval giữ tính chính xác viện dẫn và hỗ trợ ngôn ngữ tự nhiên. Không thêm baseline/reranker/fine-tuning chỉ để mở rộng phạm vi. SQLite phục vụ local; kết quả retrieval không tự tương đương PostgreSQL.
