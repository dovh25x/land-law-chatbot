# Embedding tài liệu trên Colab CPU

Notebook: `notebooks/colab_cpu_embeddings.ipynb`. Chỉ dùng tài liệu công khai đã chuẩn hóa. Không cần GPU, API key hoặc bật billing. Model E5-small ONNX Q8, tokenizer và cách xử lý cửa sổ được khóa trong worker; kết quả là vector 384 chiều. Colab Free không bảo đảm tài nguyên hoặc thời lượng phiên.

## Chuẩn bị

Xuất bundle từ đúng candidate đã kiểm tra nguồn:

```bash
.venv/bin/python scripts/offline_e5_colab.py export \
  data/staging/corpus-7ae55e5449449e25.json data/backups/colab-e5-input.zip
```

Bundle chỉ chứa text, title, ID, checksum, locator/trang của các đoạn nguồn công khai và worker. Không chứa `.env`, API key, lịch sử hội thoại hoặc vector provider cũ. Notebook khóa checksum worker; sau khi sửa worker cần tạo lại notebook/bundle cùng phiên bản.

## Chạy

1. Mở https://colab.research.google.com/ → File → Upload notebook → chọn notebook trên.
2. Runtime → Change runtime type → CPU, rồi chạy lần lượt các cell.
3. Cho phép notebook kết nối Drive của bạn. Upload duy nhất `colab-e5-input.zip` khi cell yêu cầu.
4. Checkpoint nằm trong `MyDrive/HanoiLandLawEmbeddings/<input-sha256>/`. Giữ thư mục này nếu phiên Colab bị ngắt; mở lại notebook, upload cùng bundle và chạy lại để tiếp tục.
5. Khi toàn bộ đoạn có vector, cell cuối kiểm tra và tải `colab-e5-complete.zip`. Tệp cũng nằm trong thư mục checkpoint trên Drive.

Worker tải riêng model ONNX khoảng 118 MB và SentencePiece khoảng 5 MB, kiểm tra SHA-256 trước khi dùng; chạy bằng CPUExecutionProvider. Với đoạn dài, mỗi cửa sổ được thêm tiền tố E5, không bỏ phần cuối. Checkpoint ghi và flush ngay sau mỗi vector; nếu ngắt giữa một lần ghi, lần tiếp theo chỉ bỏ dòng cuối chưa ghi đủ.

## Kiểm tra artifact

```bash
.venv/bin/python scripts/offline_e5_colab.py validate \
  data/backups/colab-e5-input.zip /path/to/colab-e5-complete.zip
```

Kết quả chỉ được công nhận hoàn chỉnh khi đủ ID đầu vào, không trùng, checksum nguồn khớp, đúng contract và mọi vector hữu hạn 384 chiều được chuẩn hóa. Artifact chưa được tự động nhập/publish. Cần hoàn thiện adapter truy vấn cùng model, migration/index 384 chiều, kiểm tra RAM container Render, backup/restore và gate demo trước khi công bố.

Có thể chạy cùng bundle trên CPU máy hiện tại làm đường dự phòng:

```bash
.venv/bin/python scripts/offline_e5_colab.py run data/backups/colab-e5-input.zip \
  --work-dir data/checkpoints/colab-e5-job \
  --output data/backups/colab-e5-complete.zip --threads 2
```

Máy chạy worker cần `onnxruntime>=1.20,<2`, `sentencepiece>=0.2,<0.3`, `numpy>=2,<3`. Notebook cài các gói này tự động. Nguồn tài liệu: https://research.google.com/colaboratory/faq.html và https://huggingface.co/intfloat/multilingual-e5-small.
