# Drivers của lần kiểm tra

Giữ các driver một lần đã thực thi để truy nguyên phương pháp và tham số. Chúng dùng output cố định và có thể sửa manifest/ghi raw; không chạy lại trực tiếp trong workspace đang vận hành. Sao chép sang checkout riêng, chọn đường dẫn output mới và đọc script trước khi tái lập. Không dùng output OCR hoặc byte-match làm receipt pháp lý.

Helper được duy trì nằm tại `scripts/prepare_corpus_candidate.py`, `scripts/evaluate_corpus_candidate.py`, `scripts/evaluate_generation_candidate.py`, `scripts/audit_corpus.py`, `scripts/ocr_offline.py` và `scripts/verify_postgres_database.py`. Script OCR batch lịch sử dùng Tesseract portable 5.5.0, traineddata tiếng Việt, 216 dpi; lần QĐ20/2023 dùng helper OCR 288 dpi. Môi trường portable ở `/tmp/landlaw-ocr` không thuộc runtime hoặc dependency triển khai.

`landlaw_probe_updated_key.py` là request chẩn đoán nhỏ tới Groq bằng Settings hiện hành, không lưu credential. Không dùng thành công của probe để suy ra khả năng chạy trọn lượt pháp lý hoặc bỏ Retry-After.
