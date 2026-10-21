# Phát hành và phục hồi an toàn

Mã ứng dụng cuối: `ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec`. Chỉ dùng receipt `render-deploy-final.jsonl` và `cloudflare-deployment-final.json` để xác định deployment thực tế. Bản đầu `bc5c0e9…` có race hiển thị lịch sử, đã được ghi nhận; không tự rollback frontend về bản đó.

Giữ `SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`, `ALLOW_STALE_GENERATION=false`. Không xoay credentials, bật generation hoặc hạ guard khi phục hồi.

## Bằng chứng được giữ

- Corpus/config trước phát hành: `before-deploy-backup.json`, SHA256 `2cce1e17af08b61165786ad88a12eab400c3a1439604a83aba235985e589ecd5`.
- Khôi phục vào PostgreSQL16 mới, riêng: `rollback-restore.json`, 60 văn bản/7.392 chunks, không conversations. Đây không phải restore thử trên cloud PG17.
- Sau cutover vẫn giữ corpus cũ `corpus-a26bc99e541fbbe2` và corpus mới `corpus-1afca764aa6692e0`; xem `corpus-publication.json` và `post-publication-database.json`.
- Deployment trước đó giữ nguyên, không xóa; các bản cũ không mặc nhiên được công nhận giữ đủ safety guards của phiên bản cuối.

## Thao tác khi có lỗi

1. Kiểm `/readyz` và `/api/v1/status` qua canonical signed ingress. Không gửi chat để kiểm tra tình trạng. Đối chiếu fingerprint `8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464` và generation tắt.
2. Nếu lỗi corpus, giữ code an toàn cuối. Operator dùng administrator connection hiện có trong bộ nhớ, tạo `Store` bằng cấu hình quản trị rồi gọi `store.publish('corpus-a26bc99e541fbbe2')`; đóng kết nối sau đó. Chỉ đổi active/previous pointers, không xóa dữ liệu. Corpus cũ chưa có receipts theo gate mới, vì vậy danh sách đoạn được review phải rỗng. Đây là từ chối an toàn khi mất coverage, không phải khôi phục đủ chức năng cũ.
3. Kiểm lại catalog rỗng và generation tắt. Nếu không bảo đảm an toàn, ngừng demo cloud và dùng nguồn đã review trong gói offline có nhãn thời điểm. Không phục hồi frontend cũ có race hoặc generation chưa kiểm chứng.
4. Nếu lỗi triển khai, kiểm deployment ID đang chạy trước khi gửi request deploy khác. Tiếp tục monitor bằng `--deployment-id`; chỉ redeploy SHA đã test khi cần. Không đổi plan Free.
5. Nếu cần restore thật do hỏng dữ liệu, kiểm checksum rồi restore vào database mới cách ly trước. Không ghi đè serving DB, DROP, phục hồi server history hay corpus đa dự án. Production restore là thao tác phục hồi riêng phải được review.

```bash
# Chỉ thực hiện khi phục hồi thực sự cần; không chạy lại cả chuỗi một cách mù quáng.
.venv/bin/python scripts/deploy.py backend --commit ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec --receipt reports/deployments/recovery-new-unique-name.jsonl
.venv/bin/python scripts/deploy.py frontend --commit ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec
```

Lần phát hành này không thực hiện rollback production. Kiểm backup/restore local chỉ chứng minh dữ liệu phục hồi được trong môi trường đã ghi. Receipt corpus không chứa source-review rows; import/activate từ bundle đúng checksum riêng. Receipt hết hạn phải được review lại; không sửa `checked_at` để làm fresh.
