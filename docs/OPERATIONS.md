# Vận hành và phục hồi

Render Free một worker; Cloudflare Pages/Function; Supabase PostgreSQL/pgvector. Không OCR hoặc chạy model sinh trên Render. Bí mật theo `.env.example`, không đưa vào Markdown hoặc `VITE_*`. VITE chỉ có URL công khai và Turnstile site key.

## Ingress, quota và dữ liệu

Cloudflare giữ `INGRESS_SECRET` trùng Render, `BACKEND_ORIGIN` cố định, lấy CF-Connecting-IP và ký method/path/query/timestamp/IP/body SHA256. Backend kiểm tra cửa sổ 60 giây, không tin X-Forwarded-For. Turnstile server-side yêu cầu hostname chính và action `create_session`. Chỉ gọi API qua Pages.

Production provider cố định scope public; CLI/dev entrypoint scope operator. Public mặc định 100 request LLM/ngày và ngừng nhận thêm khi usage ghi nhận đạt 100.000 token/ngày; retry tính vào request. Token threshold không phải trần tuyệt đối vì request đang chạy và lỗi không trả usage. Operator thống kê riêng, không chịu quota ứng dụng, vẫn tuân thủ quota thực/Retry-After Groq. Giữ hai lượt đồng thời, quota phiên/IP, cooldown chung. Có thể đặt `GENERATION_ENABLED=false` trong cửa sổ đánh giá hoặc sự cố; thư viện nguồn vẫn hoạt động.

Migration 006 xóa payload messages/traces/cache cũ và thu hồi quyền runtime. Không backup hội thoại. JSON log chỉ request ID, mã kết quả, thời gian và usage; không nội dung/credential. `land-law cleanup` chỉ xóa metadata hết hạn; workflow operations chạy mỗi giờ, thất bại tạo thông báo GitHub Actions theo cấu hình notification của operator.

## Nguồn quá hạn

Nguồn quá 7 ngày hoặc receipt changed/unavailable chặn generation. Receipt unchanged chỉ hợp lệ sau khi operator kiểm tra nội dung, checksum, văn bản sửa đổi/thay thế, quan hệ pháp lý và thời điểm; URL truy cập được không đủ. Dùng `land-law review-source <receipt.json>` với quyền owner. Schema receipt xem `backend/landlaw/ops.py`. Không tự sửa checked_at để vượt freshness. Sau restore phải kiểm tra freshness/receipt, vì backup corpus không mặc nhiên chứng minh nguồn còn mới.

## Corpus Release và restore

![Vòng đời corpus](diagrams/corpus-lifecycle.svg)

`scope_corpus.py` giữ Vành đai 4 và luật chung, tái sử dụng embedding, sửa quan hệ/gaps theo document ID. Corpus mới 59 tài liệu/7.555 chunk đã được tạo local. Không publish URL hoặc tuyên bố active trước khi các bước cloud thực hiện.

```bash
land-law backup --output data/backups/public-corpus.json
python scripts/package_release.py --help
sha256sum -c SHA256SUMS
DATABASE_URL='<database riêng>' ADMIN_DATABASE_URL='' land-law restore corpus-backup.json
```

Release gồm corpus-only JSON, SHA256SUMS và manifest corpus ID/source commit/hash nguồn/trạng thái working tree. Không có session/secret/model cache. Restore vào database riêng, kiểm tra document/chunk counts, checksum, scope, embedding contract, quyền runtime và truy xuất. `scripts/verify_postgres_restore.py` diễn tập trên schema tạm riêng bằng owner/runtime roles và xóa schema tạm trong finally; artifact ghi rõ phạm vi này. `scripts/verify_postgres_database.py` kiểm tra thêm trên database mới, rồi xóa duy nhất database tạm của lần chạy; không đụng database phục vụ.

Chỉ chuyển active sau restore đạt. Sau đó xóa corpus nhiều dự án khỏi dữ liệu/cache vận hành và gỡ asset Release cũ. Giữ báo cáo lịch sử và bản ghi thu hồi, không viết lại Git. Rollback chỉ tới corpus một dự án và code không lưu hội thoại; nếu chưa có bản phù hợp, tắt generation.

## Triển khai và xác minh

![Triển khai và phục hồi](diagrams/deploy-recovery.svg)

Deploy source đã kiểm thử/push, ghim SHA; workflow dùng concurrency để tránh hai deploy. Pages phải bundle `frontend/functions`, cấu hình secret ingress và origin backend. Render không tự chọn commit mới nhất chưa kiểm tra. Kiểm tra commit thực tế, corpus/model/fingerprint sau deploy.

Live smoke phải đi qua Cloudflare: LLM thật → hỏi tiếp → nguồn/trace ở client → reload → xóa; mobile và token sai. Không dùng luồng source-only để tuyên bố generation đạt. Nếu bị quota hoặc quyền cloud, ghi lỗi thực tế. Clone sạch chỉ được coi tái lập khi URL Release mới tồn tại và restore thành công.

Nội dung được truyền qua Cloudflare/Render tới Groq. [Chính sách Groq](https://console.groq.com/docs/your-data) phân biệt usage metadata và nội dung; vẫn có ngoại lệ lưu phục vụ reliability/abuse khi chưa bật ZDR. Cần xác minh cấu hình retention/data controls của tài khoản Groq trước khi khẳng định Zero Data Retention; repo không tự chứng minh setting đó. Không cam kết dữ liệu không rời trình duyệt: chỉ lịch sử dài hạn thuộc client.
