# Vận hành MVP

## Cấu hình
Dùng `.env.example`. Backend chỉ cần GROQ_API_KEY, model E5 và corpus; cloud bổ sung DATABASE_URL TLS, IP_HASH_SECRET ổn định và CORS_ORIGINS chính xác. APP_ENV=production chỉ biểu thị môi trường hosting, không tuyên bố chất lượng production-ready. Giữ một worker trên Render Free. Không bật billing/nâng gói.

GROQ_MODEL=openai/gpt-oss-120b mặc định; có thể chốt 20B nếu tài khoản không khả dụng, nhưng phải chạy lại 20 câu và cập nhật báo cáo. Không tự fallback. Khóa provider khác trong `.env` cá nhân không được sử dụng và không đưa lên Render.

## Dữ liệu và local
Gói bàn giao chứa `data/demo/corpus-backup.json`, không chứa hội thoại. Clone repo cần lấy backup này từ gói hoặc từ người bàn giao. Khôi phục theo README vào SQLite riêng. Nguồn/raw/model caches nằm ngoài Git. Để tái tạo từ nguồn cần tải tài liệu trong manifest, kiểm tra nội dung và dùng `land-law ingest`; không bắt buộc thu thập hoặc embedding lại để chạy bài nộp. `scripts/offline_e5_colab.py` và notebook giữ phương pháp E5 đã dùng.

## Đánh giá 20 câu

```bash
.venv/bin/land-law benchmark --split smoke --mode agentic --concurrency 1
.venv/bin/python scripts/export_mvp_evaluation.py --run-dir reports/runs/<run-id>
```

Suite ở `data/evaluation/smoke.jsonl`, checksum tại freeze.json; thay suite phải khóa lại trước chạy. Run lưu checkpoint và mọi attempt; giới hạn provider được tôn trọng. Rà soát `reviews.json` theo rubric/nguồn, gắn đúng answer_sha256; không sao chép review cũ sang đáp án mới. Khi đủ 20 ca, xuất lại với `--public-summary reports/latest.json`. Điền đủ review không đồng nghĩa mọi câu đạt.

## Backup

```bash
.venv/bin/land-law backup --output data/backups/public-corpus.json
# Chỉ khôi phục vào database riêng, không đè cloud đang chạy:
.venv/bin/land-law restore data/backups/public-corpus.json
```

Mặc định không backup phiên. Backup có phiên cần mã hóa và khóa riêng. Giữ corpus snapshot canonical và backup công khai; không xóa chúng khi dọn cache.

## Deploy
Sau kiểm thử và commit/push, chạy `python scripts/configure_render.py` để cấu hình service Free hiện có, `python scripts/deploy.py backend`, và `python scripts/deploy.py frontend`. Cần token chủ tài khoản trong `.env` hoặc CI Secrets; không đưa khóa lên chat. Deploy thủ công GitHub Actions có thể chạy trên commit đã kiểm tra. Xác minh /readyz, fingerprint báo cáo, chat thật, nguồn, trace và mobile sau deploy.

Backend ngủ: chờ cold start khoảng một phút rồi thử lại. 429: tôn trọng Retry-After. Database mất kết nối: không coi đáp án chưa lưu là thành công. Khi model/runtime đổi, báo cáo cũ phải hiện không khớp cho tới khi có đánh giá mới.
