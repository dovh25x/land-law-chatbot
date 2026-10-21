# Legal source review — phạm vi candidate

Kiểm tra trực tiếp ngày 21/10/2026 (Việt Nam), bằng GET HTTPS không xác thực. Bằng chứng transport ở `source-access*.json`; nội dung đã đọc ở `source-text/`. Không đổi raw source, corpus snapshot, chunk, vector hoặc mô hình. Receipt là review kỹ thuật có căn cứ, không phải chứng nhận pháp lý độc lập.

Không coi HTTP 200, PDF trùng checksum, hoặc sơ đồ quan hệ trống là bằng chứng văn bản còn hiệu lực toàn bộ. Không thể truy cập trang thuộc tính VBPL của QĐ 40 qua kết nối hiện tại; QĐ 56 trả403 và giữ unknown. NQ 90 tải được PDF ảnh nhưng chưa review trực quan/OCR đối chiếu đủ, nên không cấp quyền phát claim.

| Nguồn | Phần được duyệt | Ngày hỏi được phép `[from,to)` | Trạng thái |
|---|---|---|---|
| 31/2024/QH15 | Điều 91/95/104/108/109 và parent context; chỉ bản gốc trong khoảng lịch sử (15 đoạn) | 2024-08-01 → 2025-01-01 | Review theo phạm vi; toàn văn vẫn stale |
| 43/2024/QH15 | Điều 1 và5; đặc biệt khoản2 Điều 1 sửa ngày hiệu lực của Luật 31 (3 đoạn) | 2024-08-01 → 2025-01-01 | Review theo phạm vi; toàn văn vẫn stale |
| 88/2024/NĐ-CP | Điều 19/30/31; không suy quy định gốc là chính sách2026 (7 đoạn) | 2024-08-01 → 2025-07-01 | Review theo phạm vi; toàn văn vẫn stale |
| 151/2025/NĐ-CP | Điều 5 và21; phân biệt Chủ tịch UBND xã với UBND xã (10 đoạn) | 2025-07-01 → 2025-08-15 | Review theo phạm vi; toàn văn vẫn stale |
| 10/2026/QĐ-UBND | Điều 2/3 của Quyết định; bãi bỏ một phần QĐ 38 (2 đoạn) | 2026-01-18 → 2026-04-02 | Review theo phạm vi; toàn văn vẫn stale |
| 40/2026/QĐ-UBND | Chỉ Điều 2 của Quyết định, PDFpage1: ngày hiệu lực và thay thế; không phải Điều 2 của Quy định kèm theo (1 đoạn) | 2026-01-01 → 2026-10-28 | Review theo phạm vi; toàn văn vẫn stale |
| QĐ 56/2024 Hà Nội | Không được duyệt từ nguồn gốc đang403 | Không mở claim dựa trên nguồn này | unknown; receipt unavailable |
| NĐ 226/2025; NĐ 49/2026; QĐ 38/2025; Luật Thủ đô2026 | Đã tải/đối chiếu các phần liên quan để giới hạn phạm vi, chưa review đủ nguồn+quan hệ để phát claim hiện hành toàn phần | Không mở thêm từ lần truy cập | stale |
| NQ 90/2026 Hà Nội | PDF ảnh đã tải và hash khớp, chưa review nội dung đủ | Không mở claim | stale |
|48 nguồn còn lại | Chưa kiểm chứng trực tiếp trong vòng này | Không mở claim mới | stale |

Kết quả: sáu nguồn có38 đoạn được review theo thời điểm; không có văn bản nào được chứng nhận fresh toàn bộ. Toàn corpus vẫn59stale +1unknown. Cổng candidate dùng receipt có scope, không dùng phép all-fresh trên60 văn bản để quyết định mọi câu hỏi.

## Nội dung review và quan hệ cần giữ

### 31/2024/QH15

Reviewed the native official PDF part 2, physical pages 1-2,5-7,12,14-16. Article 91(5)-(6) covers infrastructure and approval/resettlement before acquisition, not a personal guarantee. Article 95(1) enumerates eligible classes; 95(2) adds alternative conditions only for those classes; 95(3) delegates additional cases. Article 104 covers disassembly, movement, installation and machine-line damage during these operations, not every loss; province sets rates. Article 108 enumerates support with branch-specific conditions and delegated detail, not automatic universal entitlement. Article 109(1) has explicit target groups and limits; (2)-(6) do not remove these prerequisites. Law43 changes commencement through252(1), not these articles. Approval is limited to the original-law historical period; no conclusion that these original rules alone govern2026. S06 model failure remains unchanged.

Receipt canonical SHA256: `a866360e6bbb04b659548f10f4e228a97ff8b1a2d72b6dd3ae3a273db3ae84bb`. File: [luat-dat-dai-2024](receipts/luat-dat-dai-2024.json).

### 43/2024/QH15

Read both native official pages. Article1(2) changes252(1) to01/08/2024 except252(2)-(3); Article1 also addresses251/255/260 and Article5 starts this law01/08/2024. Does not amend91/95/104/108/109. Historical scope only; no blanket certificate for later legislative relations.

Receipt canonical SHA256: `da95b452cc1946b6871b885cedbda25aef8b06f9e22c2d2ffec8692ffecd0565`. File: [luat-43-2024](receipts/luat-43-2024.json).

### 88/2024/NĐ-CP

Read official Government full text Articles19/30/31 and compare retained chunks. Article19(1) requires agricultural land and compensation eligibility, branches by area loss/relocation/destination;19(2) delegates separately for below30percent, ineligible land and contracted land. Article31(1) acquisition but no approved plan differs from31(2) both decisions approved before commencement: continue the approved plan, delayed payment under law at acquisition-decision date.31(3)-(5) have distinct frameworks/special policies/costs. Article30 commences01/08/2024, repeals47/2014 and06/2020 with specified partial repeals. Stop scope before two-tier government01/07/2025;226/2025 later amends19/31,49/2026 later amends19. No2026 support calculation approved.

Receipt canonical SHA256: `2c51d9f20a82a35aec157fba09d60b4b1e009c30d91ca4e330d61d6c173cd928`. File: [nd-88-2024](receipts/nd-88-2024.json).

### 151/2025/NĐ-CP

Read native official part1: Article5 heading and1(d) transfer approval under87(3)(c) to CHAIRPERSON of commune-level People Committee. Preserve distinct other subsections and exceptions. Article21 starts01/07/2025, duration and newer-law precedence. Stop before226/2025 effective15/08/2025.49/2026 Article16(3)(dd/e) later partially repeals5 with exceptions, not retroactive to02/07/2025. This receipt does not authorize filing/contact/procedure claims.

Receipt canonical SHA256: `57da6721584d1a120d14dd30c9283f9cce7c02892c827f9aa5a65d2833b428f5`. File: [nd-151-2025](receipts/nd-151-2025.json).

### 10/2026/QĐ-UBND

Read all5 official pages and compare QD38 original5pages. Decision Article2 repeals only Article2 ofQD38/2025 plus wholeQD47/2016; it does not repeal allQD38. Article3 commences18/01/2026. QD566 correction concerns Article1(5) amount-in-words, not these clauses. QD40 replacesQD10 from02/04/2026. No compensation amounts or current authority claims approved.

Receipt canonical SHA256: `792006ce16276b24abb012912a78f89ad6e267dea57f6c44469b421101dd1e8b`. File: [qd-10-2026-hanoi](receipts/qd-10-2026-hanoi.json).

### 40/2026/QĐ-UBND

Read native official decision page1 Article2 (distinct from attached Regulations Article2), pages3(scope) and18(Article29 transition). Article2 explicitly commences02/04/2026 and replacesQD47/2016,QD56/2024,QD38/2025,QD10/2026. This verifies the replacement/commencement fact only, including retrospective questions predating commencement. It does NOT establish that every attached substantive rule currently governs a household. Article29 preserves qualifying approved additional policies and ongoing delegated authority, not all old rates or all old decisions. Reviewed49/2026 Articles11/16/19 and226/2025 amendment/transition chronology as dependencies. LuatThuDo2026 Articles24/35/36 and NQ 90 introduce conditional special-policy/transition considerations. No current rate, multiplier, entitlement or filing authority is enabled. Registry unavailable; diagram lists relation headings but empty edges, not proof of absence of later changes. The question-date window for this static replacement/commencement fact ends28/10/2026, bounded by the seven-day review horizon; this is not approval of future substantive rights. A changed/unavailable receipt still vetoes immediately.

Receipt canonical SHA256: `759169da0f4d32c57b58002630d855bf95aa39ede71375468ec41530a4770fec`. File: [qd-40-2026-hanoi](receipts/qd-40-2026-hanoi.json).

## Phạm vi sử dụng và phần chưa khép

- Có mapping đủ32 ca khóa tại [SCOPE_MAPPING.md](SCOPE_MAPPING.md);20 ca cógold đều nằm trong scope tại ngày hỏi. Đây là source coverage, không phải Answer Correctness. S06 vẫn giữ FAIL ở attempt model cuối; không gọi lại hoặc đổi verdict.
- Phần lớn ca nội dung trong suite hỏi tại02/08/2024. Chúng không chứng minh chatbot trả lời được câu hỏi mặc định ngày hiện tại.
- Với ngày hiện tại, policy chỉ mở facts hiệu lực/thay thế củaQĐ40. Các câu hỏi nội dung bồi thường/hỗ trợ/tái định cư hiện hành nhìn chung sẽ bị hạn chế hoặc từ chối. Đây là gap có thật của MVP hiện hành, không được che bằng số20/20source coverage.
- Muốn mở nhóm câu hỏi hiện hành, cần review đúng các phần phụ thuộc: NQ 254 Điều 3/7/13 và bản ảnh chính thức, NĐ 49 Điều 11/16/19, NĐ 226 Điều 2/7/8, Quy định kèmQĐ40 (phân biệt phạm vi, chủ thể vàĐiều29), Luật Thủ đô2026 Điều 24/35/36 và chính sách HĐND có liên quan. NQ 258/NQ 90 chỉ áp dụng khi xác định đúng loại dự án và chuyển tiếp; không tự suyVành đai4 được nhận mức đặc thù.
- Không xác định thửa đất, tính tiền, bảo đảm suất tái định cư hoặc chỉ dẫn nơi nộp hồ sơ chưa được duyệt. Nguồn không mở vẫn có thể đọc trong thư viện; không được dùng làm citation cho claim của candidate.

Các nguồn chính thức tiêu biểu: [Luật 43](https://vanban.chinhphu.vn/?pageid=27160&docid=211201), [Luật 31 bản gốc phần2](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/31-2024-qh15_2.pdf), [NĐ 88 toàn văn Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-quy-dinh-ve-boi-thuong-ho-tro-tai-dinh-cu-khi-nha-nuoc-thu-hoi-dat-119240906111916662.htm), [QĐ 40 bản chính thức](https://datafiles.hanoi.gov.vn/gov-hni/6249/VanBanCongBao/2026/5/29/QDPQ-40-2026_signed.pdf), [Luật Thủ đô2026](https://congbao.chinhphu.vn/van-ban/luat-so-02-2026-qh16-469529.htm).
