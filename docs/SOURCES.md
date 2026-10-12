# Danh mục và kiểm tra nguồn

Thời điểm tải và đối chiếu: 11–12/10/2026 UTC; snapshot QĐ56 được lấy và kiểm tra ngày 12/10. Đây là bộ nguồn kỹ thuật đã thu thập từ cơ quan công bố chính thức; việc đọc toàn văn và kiểm tra metadata không thay thế thẩm định pháp lý độc lập. Manifest lưu URL công bố, bản tải, checksum và trạng thái kiểm tra; không chứa tài liệu giả.

## Độ bao phủ thực tế

| Nhóm | Danh mục | Toàn văn đã kiểm tra | Chờ kiểm tra/cách ly |
|---|---:|---:|---:|
| Văn bản pháp lý | 40 | 32 | 8 |
| Vành đai 4 | 6 | 1 nghị quyết + 4 bài chính thức | 1 nghị quyết PDF ảnh |
| Trục đại lộ cảnh quan sông Hồng | 5 | 5 | 0 |
| Khu đô thị thể thao Olympic | 5 | 5 | 0 |

Tổng cộng 56 nguồn, 28 quan hệ pháp lý có vị trí điều khoản và URL chứng minh. Số lượng văn bản đã kiểm tra đáp ứng mức 30 văn bản pháp lý, toàn văn lịch sử QĐ56 đã bổ sung; NQ106/NQ-CP và các nguồn khác còn cách ly được ghi trong coverage_gaps. Không đánh dấu M1 hoàn tất chỉ từ số lượng.

## Kết quả kiểm tra quan trọng

- QĐ 40/2026/QĐ-UBND: đã tải bản Công báo Hà Nội, đủ số/ngày. Điều 2 thay thế QĐ 47/2016, QĐ 56/2024, QĐ 38/2025 và QĐ 10/2026 từ 02/04/2026. Điều 29 của Quy định kèm theo phải được đọc cho chuyển tiếp.
- QĐ 56/2024/QĐ-UBND: đã lấy toàn văn từ [bản hiển thị chính thức VBPL](https://vbpl.vn/hanoi/Pages/ivbpq-toanvan.aspx?ItemID=169992&Keyword=) qua snapshot của công cụ web. Hai cửa sổ chồng lấp bao phủ đủ 391 dòng, phần chồng khớp nhau. Bản giữ có số 56, ngày 06/09/2024, ngày hiệu lực 20/09/2024, chữ ký, ba điều của quyết định và 28 điều quy định kèm phụ lục. Chuẩn hóa chỉ bỏ navigation/marker công cụ và giữ nguyên nội dung; checksum bản gốc và chuẩn hóa lưu trong manifest và Storage private. Snapshot được công cụ ghi nhận đã crawl khoảng năm tháng trước, nên ngày 12/10 là ngày lấy/kiểm tra snapshot, không phải chứng nhận nguồn được crawl mới trong ngày. Footer mẫu VBPL ghi “Ủy ban nhân dân tỉnh” khác phần quyết định Hà Nội; giữ và công khai khác biệt mẫu, không chỉnh văn bản. Mốc hết hiệu lực 02/04/2026 được đối chiếu trực tiếp Điều 2 QĐ40. Bản PDF draft số/ngày trống tiếp tục bị loại. Không coi snapshot này là PDF ký số gốc hay thẩm định pháp lý độc lập; không phục dựng từ search snippet. Chi tiết tại reports/source-discovery.json.

- QĐ 38/2025 và QĐ 10/2026 có quan hệ bãi bỏ một phần. Quan hệ repeals có locator chỉ điều khoản bị tác động, không biểu thị toàn văn hết hiệu lực tại mốc sửa đổi.
- QĐ 566/QĐ-UBND ngày 05/02/2026 đính chính phần chữ của 10.000.000 đồng trong QĐ 10/2026; giữ nguyên giá trị số.
- Bảng giá tại QĐ 71/2024 được tải đủ ba phần Công báo. Kỳ áp dụng kết thúc 31/12/2025. provision_validity.effective_to=2026-01-01 giới hạn kỳ bảng giá; effective_to toàn văn để null vì chưa có chứng cứ bãi bỏ toàn bộ. NQ 52/2025/NQ-HĐND gồm ba phần đã tải, áp dụng bảng giá từ 01/01/2026; QĐ 89/2025 và QĐ 19/2026 cung cấp các hệ số liên quan. Không tự tính tiền bồi thường từ bảng/hệ số.
- Luật Thủ đô 02/2026/QH16 đã tải toàn văn Công báo. Điều 35: hiệu lực chung 01/07/2026; khoản 4 Điều 8 và khoản 6 Điều 36 từ ngày thông qua 23/04/2026. Luật Thủ đô 39/2024 được giữ làm nguồn lịch sử; đối chiếu Điều 36 về chuyển tiếp. Manifest thêm provision_validity riêng cho khoản 4 Điều 8 và khoản 6 Điều 36 từ 23/04/2026, được Điều 35 khoản 2 và dòng kết toàn văn xác nhận trực tiếp.
- Luật Khiếu nại 2011 phải đọc cùng Luật 136/2025, có hiệu lực 01/07/2026. Luật Quy hoạch đô thị và nông thôn 47/2024 phải đọc cùng Luật 144/2025.
- Các nghị định 71, 88, 101, 102 và 151 được liên kết sửa đổi tại NĐ 226/2025. Điều 8 của NĐ 226 có chuyển tiếp phụ thuộc mốc phê duyệt/ban hành, không chỉ phụ thuộc ngày hỏi.

## Khoảng trống không được suy diễn

Chưa thu thập toàn văn NQ 254/2025/QH15, NQ 258/2025/QH15 và toàn bộ chính sách đặc thù Hà Nội ban hành năm 2026 được các nguồn dẫn chiếu. NĐ 49/2026 và Luật Thủ đô mới cung cấp một phần căn cứ nhưng không thay thế văn bản được hướng dẫn. Những câu hỏi đòi hỏi quy định đặc thù chưa có phải trả lời giới hạn và nêu nguồn cần đối chiếu. Danh mục sửa đổi/đính chính sau NĐ 178/2025 và văn bản xử phạt cũng chưa được xác minh đầy đủ; không khẳng định corpus là bản hợp nhất của mọi luật tại ngày phát hành.

Nguồn sông Hồng và Olympic hiện chủ yếu là thông tin chính thức. Bài Viện Quy hoạch nêu các quyết định phê duyệt nhưng chưa tải được toàn bộ quyết định/bản đồ tương ứng. Bài Olympic khu B nói về **nhiệm vụ quy hoạch**, không chứng minh đã phê duyệt đồ án. Tin khởi công/tiến độ không chứng minh một hộ đủ bồi thường hay một thửa nằm trong ranh giới thu hồi.

## Lỗi nguồn và cách xử lý

- Các URL VBPL legacy có thể trả HTTP 200 nhưng chỉ là trang Next.js “Đang tải dữ liệu”; không xem HTTP 200 là bằng chứng có toàn văn. Domain vbpl.moj.gov.vn gặp lỗi DNS/502; các tài nguyên frontend công khai nhận 403. QĐ 10/2017 và QĐ 20/2023 chỉ giữ nguồn staging.
- Một số tệp của vanban.hanoi.gov.vn có metadata đúng nhưng nội dung PDF là bản dự thảo chưa điền số/ngày. Các bản QĐ 40/2026, 55/2024, 61/2024, 71/2024, 38/2025, 10/2026, 40/2025 và 27/2024 đã được thay bằng bản Công báo trong raw_paths. Bản tải cũ còn trong data/raw để kiểm tra sự cố, không được tự động index toàn thư mục.
- CDN g7.cdnchinhphu.vn có lỗi chứng chỉ khi tải một số bản mới. Không tắt TLS verification. Dùng URL congbaocdn.chinhphu.vn có trong data-href của chính trang Công báo để tải PDF thật.
- PDF ảnh có OCR sidecar đặt theo PDF.with_suffix(".ocr.txt"), phân trang bằng form-feed. Manifest ocr_sidecars gắn checksum PDF và OCR; review_status=pending/ocr_reviewed=false cho đến khi rà số/ngày/số liệu. Không công bố OCR chỉ vì công cụ chạy xong. Tesseract chỉ chạy ngoại tuyến, không cài vào backend Render.
- HTML xaydungchinhsach nên lấy .detail__content và loại widget bài liên quan; Luật Khiếu nại trên vanban.chinhphu lấy #block_detail.document-detail, tránh header/menu/footer. Trang dự án Viện Quy hoạch lấy #news-bodyhtml; baochinhphu.vn lấy .detail-content và bỏ mục Tham khảo thêm.

## Nguồn pháp lý đã tải và kiểm tra

| ID ổn định | Văn bản | Hiệu lực chung đã đối chiếu | Nguồn công bố |
|---|---|---|---|
| `luat-dat-dai-2024` | 31/2024/QH15 | 2024-08-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=211189) |
| `luat-43-2024` | 43/2024/QH15 | 2024-08-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=211201) |
| `nd-88-2024` | 88/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-quy-dinh-ve-boi-thuong-ho-tro-tai-dinh-cu-khi-nha-nuoc-thu-hoi-dat-119240906111916662.htm) |
| `nd-71-2024` | 71/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-71-2024-nd-cp-42155.htm) |
| `nd-101-2024` | 101/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-101-2024-nd-cp-quy-dinh-dang-ky-cap-giay-chung-nhan-quyen-su-dung-dat-quyen-so-huu-tai-san-gan-lien-voi-dat-119240801170006295.htm) |
| `nd-102-2024` | 102/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-102-2024-nd-cp-42485/51276.htm) |
| `nd-103-2024` | 103/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-103-2024-nd-cp-42499.htm) |
| `nd-104-2024` | 104/2024/NĐ-CP | 2024-08-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-104-2024-nd-cp-42495.htm) |
| `nd-151-2025` | 151/2025/NĐ-CP | 2025-07-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-151-2025-nd-cp-45191.htm) |
| `nd-226-2025` | 226/2025/NĐ-CP | 2025-08-15 | [Nguồn](https://xaydungchinhsach.chinhphu.vn/nghi-dinh-226-2025-nd-cp-sua-doi-bo-sung-cac-nghi-dinh-quy-dinh-thi-hanh-luat-dat-dai-119250817114021905.htm) |
| `nd-49-2026` | 49/2026/NĐ-CP | 2026-01-31 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-49-2026-nd-cp-468908.htm) |
| `qd-56-2024-hanoi` | 56/2024/QĐ-UBND | 2024-09-20; hết hiệu lực 2026-04-02 | [Snapshot nguồn chính thức](https://vbpl.vn/hanoi/Pages/ivbpq-toanvan.aspx?ItemID=169992&Keyword=) |
| `qd-38-2025-hanoi` | 38/2025/QĐ-UBND | 2025-07-01 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=4875&pageid=45002) |
| `qd-10-2026-hanoi` | 10/2026/QĐ-UBND | 2026-01-18 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5204&pageid=45002) |
| `qd-40-2026-hanoi` | 40/2026/QĐ-UBND | 2026-04-02 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5335&pageid=45002) |
| `qd-55-2024-hanoi` | 55/2024/QĐ-UBND | 2024-09-16 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=1904&pageid=45002) |
| `qd-61-2024-hanoi` | 61/2024/QĐ-UBND | 2024-10-07 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=1917&pageid=45002) |
| `qd-71-2024-hanoi` | 71/2024/QĐ-UBND | 2024-12-20 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=4654&pageid=45002) |
| `qd-40-2025-hanoi` | 40/2025/QĐ-UBND | 2025-07-01 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=4877&pageid=45002) |
| `luat-thu-do-2024` | 39/2024/QH15 | 2025-01-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=211197) |
| `luat-quy-hoach-do-thi-2024` | 47/2024/QH15 | 2025-07-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=212475) |
| `luat-144-2025` | 144/2025/QH15 | 2026-01-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=216526) |
| `nd-178-2025` | 178/2025/NĐ-CP | 2025-07-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-178-2025-nd-cp-45368.htm) |
| `qd-27-2024-hanoi` | 27/2024/QĐ-UBND | 2024-04-20 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=1805&pageid=45002) |
| `luat-khieu-nai-2011` | 02/2011/QH13 | 2012-07-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=162374) |
| `luat-136-2025` | 136/2025/QH15 | 2026-07-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/luat-so-136-2025-qh15-468696.htm) |
| `luat-nha-o-2023` | 27/2023/QH15 | 2024-08-01 | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=209627) |
| `luat-thu-do-2026` | 02/2026/QH16 | 2026-07-01 | [Nguồn](https://congbao.chinhphu.vn/van-ban/luat-so-02-2026-qh16-469529.htm) |
| `qd-566-2026-hanoi` | 566/QĐ-UBND | 2026-02-05 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5255&pageid=45002) |
| `nq-52-2025-hanoi` | 52/2025/NQ-HĐND | 2026-01-01 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5054&pageid=45002) |
| `qd-89-2025-hanoi` | 89/2025/QĐ-UBND | 2026-01-01 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5098&pageid=45002) |
| `qd-19-2026-hanoi` | 19/2026/QĐ-UBND | 2026-02-02 | [Nguồn](https://congbao.hanoi.gov.vn/Default.aspx?p_attribute=5252&pageid=45002) |

## Nguồn pháp lý chờ kiểm tra/cách ly

| ID | Nguyên nhân | Nguồn |
|---|---|---|
| `luat-quy-hoach-2017` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=192206) |
| `luat-dat-dai-2013` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=171639) |
| `nd-47-2014` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=173972) |
| `qd-10-2017-hanoi` | VBPL legacy chỉ có trang tải | [Nguồn](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=121164) |
| `qd-30-2019-hanoi` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.hanoi.gov.vn/chi-tiet-van-ban/quyet-dinh-so-30-2019-qd-ubnd-cua-ubnd-tp-ha-noi-ve-viec-ban-hanh-quy-dinh-va-bang-gia-cac-loai-dat-189067) |
| `qd-20-2023-hanoi` | VBPL legacy chỉ có trang tải | [Nguồn](https://vbpl.vn/hanoi/Pages/vbpq-toanvan.aspx?ItemID=164473) |
| `nd-124-2020` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=201363) |
| `nd-123-2024` | PDF ảnh chưa duyệt OCR | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=211356) |

## Hồ sơ dự án

| Dự án | ID | Loại và trạng thái | Nguồn |
|---|---|---|---|
| ring4 | `ring4-nq56-2022` | project_decision / verified | [Nguồn](https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-56-2022-qh15-37456.htm) |
| ring4 | `ring4-nq106-2022` | project_decision / pending | [Nguồn](https://vanban.chinhphu.vn/?pageid=27160&docid=206398) |
| ring4 | `ring4-hadong-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-dia-phuong/quan-ha-dong-day-nhanh-tien-do-thuc-hien-du-an-vanh-dai-4-4250416202518818.htm) |
| ring4 | `ring4-hotro-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/ho-tro-toi-da-de-hoan-thanh-du-an-vanh-dai-4-vung-thu-do-4251126183340466.htm) |
| ring4 | `ring4-phuluong-2025` | official_news / verified | [Nguồn](https://phuluong.hanoi.gov.vn/chi-dao-cua-dia-phuong/phu-luong-day-nhanh-tien-do-chi-tra-boi-thuong-ho-tro-gpmb-du-an-duong-vanh-dai-4-vung-thu-do-ha-noi-2792251112170551337.htm) |
| songhong | `songhong-chuanbi-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/ha-noi-chuan-bi-khoi-cong-du-an-dau-tu-xay-dung-truc-dai-lo-canh-quan-song-hong-4251217221834883.htm) |
| songhong | `songhong-thongtin-2026` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/thong-tin-bao-chi-ve-du-an-dau-tu-xay-dung-truc-dai-lo-canh-quan-song-hong-tren-dia-ban-thanh-pho-ha-noi-4260519140629815.htm) |
| songhong | `songhong-trienkhai-2026` | official_news / verified | [Nguồn](https://hanoi.gov.vn/chi-dao-cua-thanh-uy-ha-noi/tang-cuong-lanh-dao-trien-khai-du-an-dau-tu-truc-dai-lo-canh-quan-song-hong-4260611162524587.htm) |
| songhong | `songhong-khoicong-2025` | official_news / verified | [Nguồn](https://namphu.hanoi.gov.vn/tin-tuc-su-kien/khoi-cong-truc-dai-lo-canh-quan-song-hong-du-an-chien-luoc-cua-thu-do-2721251219211950929.htm) |
| songhong | `songhong-quyhoach-2026` | official_news / verified | [Nguồn](https://vqh.hanoi.gov.vn/index.php?language=vi&nv=news&op=tin-tuc-hoat-dong%2Fthuc-hien-tuyen-truyen-pho-bien-thong-tin-quy-hoach-du-an-dau-tu-truc-dai-lo-canh-quan-song-hong-3288.html) |
| olympic | `olympic-chutruong-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/du-an-khu-do-thi-the-thao-olympic-khu-do-thi-the-thao-dap-ung-su-kien-tam-chau-luc-va-quoc-te-4251213114931408.htm) |
| olympic | `olympic-nhiemvu-khub-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/chi-dao-cua-ubnd-thanh-pho-ha-noi/phe-duyet-nhiem-vu-quy-hoach-phan-khu-do-thi-the-thao-olympic-khu-b-425111016444055.htm) |
| olympic | `olympic-chuanbi-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/ha-noi-chuan-bi-khoi-cong-khu-do-thi-the-thao-olympic-chao-mung-dai-hoi-xiv-cua-dang-4251218070139796.htm) |
| olympic | `olympic-khoicong-2025` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/khoi-cong-du-an-khu-do-thi-the-thao-olympic-tai-ha-noi-4251219143354716.htm) |
| olympic | `olympic-kiemtra-2026` | official_news / verified | [Nguồn](https://hanoi.gov.vn/tin-tuc-su-kien-noi-bat/chu-tich-ha-noi-vu-dai-thang-kiem-tra-tien-do-du-an-khu-do-thi-the-thao-olympic-426051314140978.htm) |
| ring4 | `ring4-trienkhai-2022` | official_news / verified | [Nguồn](https://baochinhphu.vn/khoi-cong-xay-dung-duong-vanh-dai-4-vung-thu-do-ha-noi-truoc-30-6-2023-102220818172858529.htm) |

## Tệp bàn giao và phát hành

- data/sources.json: manifest chuẩn, raw_paths, raw_checksums, mốc hiệu lực, ghi chú và tình trạng kiểm tra.
- data/legal_relations.json: chỉ các quan hệ đã đọc từ văn bản nguồn; quan hệ bãi bỏ một phần có locator. source_locator chỉ điều khoản của văn bản sửa đổi; target_locators chỉ điều khoản gốc đã xác định. Khi target_locators_complete=false, không được suy ra điều khoản vắng trong list chắc chắn chưa bị sửa.
- data/projects.json: mô tả thận trọng và năm nguồn đã kiểm tra mỗi dự án; câu gợi ý không khẳng định quyền lợi cá nhân.
- data/raw/: tệp tải thật cùng các báo cáo download và sidecar. Chỉ sử dụng raw_paths trong manifest; không quét tự động mọi tệp vì còn bản draft/metadata/phụ lục trùng để kiểm tra sự cố.

Khi cập nhật: tải staging, kiểm tra checksum, đối chiếu số/ngày và quan hệ cấp điều khoản, chạy regression, rồi mới tạo release. Nếu quá bảy ngày chưa đối chiếu thành công, trả lời “hiện nay” phải nêu giới hạn cập nhật. QĐ56 đã qua kiểm tra nguồn/snapshot; các OCR pending vẫn cần kiểm tra nội dung thực tế trước indexing.

Kiểm tra cấu trúc/checksum: data/raw/source_asset_audit.json. Mọi ID quan hệ hợp lệ, raw_checksums khớp tệp và mỗi hồ sơ dự án có năm source_ids verified. Kiểm tra đọc body thực tế trên toàn bộ nguồn verified đạt >1000 ký tự/nguồn; có cảnh báo font Courier CFF thiếu fontTools, cần kiểm tra chất lượng parse khi ingestion.
