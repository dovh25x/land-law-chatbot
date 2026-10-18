# Phạm vi và tiêu chí khóa trước thay đổi

Baseline: commit `2d2e7bc`, corpus `corpus-581da76c79b0b362`; không sửa artifact cũ hoặc các suite đã khóa.

Triển khai: bổ sung bảy nguồn thiếu sau kiểm tra; QĐ27 → QĐ10 và chuỗi pháp lý; provenance ảnh NQ254; sửa layout QĐ71 bằng bản chép có đối chiếu; lọc chỉ mục luật chuyên ngành theo scope rà soát, giữ vector của chunk không đổi; sửa checker phạm vi; cải thiện retrieval số hiệu/quan hệ thay thế; snapshot mới, restore riêng, đánh giá, phát hành và deploy SHA đã kiểm thử.

Tiêu chí kỹ thuật trước chuyển active:
- Không lỗi provenance/schema/checksum/parent/vector. Nguồn mới không được active nếu chưa đủ toàn văn và đối chiếu pháp lý; ghi rõ nguồn chưa thể xác minh.
- Không embedding lại chunk không đổi. Map ảnh không được tự nhận là PDF ký số.
- Giải quyết relation QĐ27 và các endpoint thiếu được xác minh; mỗi relation có nguồn/locator/scope, không suy bãi bỏ toàn văn từ sửa một phần.
- Cả SQLite và PostgreSQL riêng: raw Recall@8 không thấp hơn baseline smoke 9/11, supplemental 3/3, natural 0,75; kiểm tra S13/N06 phục hồi gold qua số hiệu/quan hệ nguồn, không hardcode case/gold. S14 query gốc không history và N03 parent annotation giữ nguyên.
- Generation chạy suite khóa 20+4 và natural trên cấu hình cuối, giữ mọi attempt và review gắn checksum. Mục tiêu natural >=5/6 ca nội dung; hạn chế/provider lỗi không bị xóa khỏi mẫu. Không phát claim chưa đủ chứng cứ.
- Backend/unit/build/E2E/secret checks đạt; restore corpus vào DB/schema riêng trước publish; Release tải lại khớp hash. Chỉ chuyển active sau cổng kiểm tra, không gỡ Release cũ trong lần làm việc này.
- Receipt freshness chỉ ghi khi đối chiếu fulltext và sửa đổi/chuyển tiếp; URL 200 không đủ. Nếu không xác minh được nguồn, giữ cơ chế chặn và ghi chưa hoàn tất.

Không đổi model, embedding contract, pipeline hoặc gói Free. Không tự xác nhận thẩm định pháp lý độc lập.
