# Source reliability — rà soát có giới hạn

## Phạm vi và trạng thái

Corpus serving/candidate giữ `corpus-a26bc99e541fbbe2`:55 văn bản pháp luật,5 nguồn dự án Vành đai4,7.392 chunks. Offline audit tái lập60/60,133 raw files khớp; không đổi source, embedding hoặc corpus. `publication_ready=false`, `dependencies_complete=false` vẫn được giữ; toàn vẹn không thay chứng nhận pháp lý.

Đã GET13 trang trọng tâm, tải lại6 bản gốc, đối chiếu điều hiệu lực/thay thế/chuyển tiếp cần thiết.12/13 trang trả200, QĐ56 trả403; cả6 PDF khớp hash snapshot. Không crawl rộng. Dữ liệu nguồn và thời điểm/checksum ở `read-only-http-checks.json`, `attachment-get-checks.json`, `source-review.json`.

**Audit disposition:59 stale,1 unknown,0 fresh,0 newly-confirmed changed.** Đây không phải đếm receipt production. Snapshot local chưa import receipt có60 stale; sau thử receipt QĐ56 trên SQLite riêng có59 stale/1unknown. Live chỉ quan sát được `source_fresh=false`; không truy vấn bảng reviews production.

- `stale`: lần rà cũ quá hạn; không tự kết luận văn bản đã đổi/hết hiệu lực.
- `unknown`: lần thử hiện tại không xác minh được nguồn, ở đây HTTP403 của QĐ56; đề xuất receipt `unavailable`, không phải `unchanged`.
- `changed`: cần bằng chứng bất lợi mới so với snapshot. QĐ56/QĐ38/QĐ10 đã được mô hình hóa là lịch sử nên không gắn changed chỉ vì đã bị thay.
- Không cấp fresh vì HTTP200/hash trùng. Các phần quan hệ mới đến20/10/2026 chưa rà đầy đủ vẫn là phần chưa xác minh.

## Nguồn trọng tâm

Mốc trong bảng là mốc theo văn bản/chuỗi được đối chiếu, không phải chứng nhận tất cả nội dung đang áp dụng ngày audit.

| Nguồn | Ban hành → hiệu lực/quan hệ | Trạng thái audit và evidence |
|---|---|---|
| [Luật31/2024/QH15](https://vanban.chinhphu.vn/?pageid=27160&docid=211189) + [Luật43/2024/QH15](https://vanban.chinhphu.vn/?pageid=27160&docid=211201) |18/01/2024 và29/06/2024; Luật43 sửa khoản1 Điều252 thành01/08/2024, có ngoại lệ trong điều hiệu lực. Không dùng riêng metadata gốc01/01/2025 |stale; trang200, PDF Luật43 hai trang hash khớp, đã đối chiếu điều sửa hiệu lực; chưa rà hết mọi sửa đổi của Luật Đất đai tới ngày audit |
| [NĐ88/2024/NĐ-CP](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-quy-dinh-ve-boi-thuong-ho-tro-tai-dinh-cu-khi-nha-nuoc-thu-hoi-dat-119240906111916662.htm) |15/07/2024 →01/08/2024; có NĐ226 và NĐ49 sửa. Điều31 phục vụ câu hỏi mốc2024, không áp nguyên bản cho mọi hồ sơ2026 |stale; HTML200; raw/chunks tái lập; quan hệ có trong corpus, chưa cấp review hiện hành mới |
| [NĐ151/2025/NĐ-CP](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-151-2025-nd-cp-45191.htm) |12/06/2025 →01/07/2025; NĐ226 sửa, Điều16 NĐ49 bãi bỏ nhiều phần có ngoại lệ |stale; trang200, raw3phần tái lập offline. S05 phải dùng ngày02/07/2025, không thay quyền hạn bằng quy định có sau ngày hỏi |
| [NĐ226/2025/NĐ-CP](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-226-2025-nd-cp-45839/58217.htm) |15/08/2025 →15/08/2025; sửa nhiều nghị định, gồm NĐ88; cần đọc tiếp NĐ49 |stale; trang200, bản44trang trong raw tái lập; chưa đọc lại toàn bộ và mọi quan hệ mới trong vòng này |
| [NĐ49/2026/NĐ-CP](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-49-2026-nd-cp-468908/62347.htm) |31/01/2026 →31/01/2026; Điều11 sửa NĐ88, Điều16 bãi bỏ từng phần, Điều19 chuyển tiếp thu hồi/bồi thường |stale; PDF37trang hash khớp, đối chiếu các điều trên. Không suy mọi phương án cũ phải làm lại |
| [QĐ40/2026/QĐ-UBND](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5335&pageid=45002) · [PDF gốc](https://datafiles.hanoi.gov.vn/gov-hni/6249/VanBanCongBao/2026/5/29/QDPQ-40-2026_signed.pdf) |02/04/2026 →02/04/2026; Điều2 quyết định thay47/2016,56/2024,38/2025,10/2026. Phân biệt với Điều2 Quy định kèm theo |stale; trang200, PDF18trang hash khớp. Upload29/05/2026 không phải ngày ban hành. Chưa xác nhận đầy đủ mọi sửa đổi mới tới20/10 |
| [QĐ56/2024/QĐ-UBND](https://vbpl.vn/hanoi/Pages/ivbpq-toanvan.aspx?ItemID=169992&Keyword=) |06/09/2024 →20/09/2024; lịch sử, QĐ40 thay từ02/04/2026 |**unknown** cho lần truy cập/rá hiện tại:403; không dùng snapshot cache để cấp fresh. Mốc thay thế được chứng minh riêng bằng QĐ40 |
| [QĐ38/2025/QĐ-UBND](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=4875&pageid=45002) |30/06/2025 →01/07/2025; Điều2 bị QĐ10 bãi, toàn văn được QĐ40 thay02/04/2026 |stale; trang/PDF5trang200, hash khớp; không đánh đồng bãi một điều với hết hiệu lực toàn bộ tại20/01/2026 |
| [QĐ10/2026/QĐ-UBND](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5204&pageid=45002) |18/01/2026 →18/01/2026; Điều2 bãi Điều2 QĐ38; QĐ40 thay từ02/04 |stale; PDF5trang khớp; đã đọc Điều2/3 và quan hệ QĐ566 |
| [QĐ566/QĐ-UBND](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5255&pageid=45002) |05/02/2026 →ngày ký; đính chính phần chữ tiền khoản5 Điều1 QĐ10 |stale; PDF2trang khớp; đính chính không phải cơ chế tính tiền mới |
| [NQ254/2025/QH15](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-254-2025-qh15-quy-dinh-mot-so-co-che-chinh-sach-thao-go-kho-khan-vuong-mac-trong-to-chuc-thi-hanh-luat-dat-dai-119251225171010998.htm) |11/12/2025 →01/01/2026 theo nguồn/metadata đã lưu; cơ chế đặc thù và chuyển tiếp, không coi là sửa toàn Luật |stale; trang200 có ảnh. Chưa đối chiếu lại15ảnh online; native parser không thấy fulltext không có nghĩa website đã hết nội dung. Không cấp fresh mới |
| [NQ56/2022/QH15 Vành đai4](https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-56-2022-qh15-37456.htm) |16/06/2022 →16/06/2022; chủ trương đầu tư, không chứng minh thửa/tiền/quyền lợi hộ |stale; trang200, raw tái lập. Chưa rà mọi sửa đổi/tài liệu triển khai mới |

47 nguồn khác chưa rà trực tiếp trong vòng này; danh sách đầy đủ cùng hiệu lực/checksum/notes giữ trong `source-review.json`. Không biến việc parser đọc được thành approval pháp lý. Bảy gap lịch sử/tham chiếu và các relation chưa giải quyết giữ nguyên trong `corpus-audit.json`; không xóa để làm coverage đẹp.

## Receipt và cổng fail-closed

`proposed-receipts/qd-56-2024-hanoi-unavailable.json` gắn đúng checksum/UTC, có relation review/evidence URLs. `source-policy-replay.json` chứng minh import vào SQLite riêng đưa source từ stale sang unknown, `source_fresh=false`. Không import production; không đánh dấu changed/unknown là stale để dùng snapshot override.

F01 local kiểm tra nguồn ở verify và finish, changed/unknown không được override. Live fingerprint còn khác candidate nên **chưa chứng nhận cổng F01 này trên deployment**. Trước demo có khẳng định pháp luật hiện hành, cần review nguồn/receipt, duyệt code, deploy SHA đã test và đối chiếu live. Không tự thay timestamp, corpus hoặc cờ generation trong Phase2.
