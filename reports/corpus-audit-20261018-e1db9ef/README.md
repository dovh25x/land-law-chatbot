# Kiểm tra chất lượng corpus ngày 18/10/2026

## Kết luận

**Chưa nên nghiệm thu corpus như một bộ nguồn đầy đủ cho mọi câu hỏi bồi thường Vành đai 4. Nên sửa và bổ sung có chọn lọc, chưa có căn cứ để xóa toàn bộ và xây lại.** Snapshot tái lập được và không phát hiện lỗi integrity, nhưng còn thiếu chuỗi nguồn lịch sử, một quan hệ sửa đổi chưa khai báo, giới hạn truy nguyên tới trang gốc và một số ca retrieval chưa tìm đúng điều khoản có sẵn.

Các thay đổi có trước lần đánh giá đã được commit tại `e1db9ef` (`Harden agent publication gates and document system flows`). Không push hoặc deploy trong lần này. Corpus kiểm tra: `corpus-581da76c79b0b362`, 59 tài liệu, 7.555 chunk; PostgreSQL thực tế đang active cùng corpus. Không thay dữ liệu đang phục vụ, không cập nhật receipt, không đổi model hoặc embedding.

## Phép kiểm tra và kết quả

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| Publication/schema/provenance | Không phát hiện lỗi; 130/130 artifact gốc khớp hash, 7.555 chunk khớp checksum, không trùng body tài liệu | [Integrity](integrity.json) |
| Tái lập parsing từ raw đã rà soát | 59/59 tài liệu tái tạo đúng ID và checksum của mọi chunk | [Log theo tài liệu](integrity-run.log), [integrity](integrity.json) |
| Embedding snapshot | Mọi vector đủ 384 chiều, hữu hạn, L2 gần 1; 6 mẫu tính kiểm tra lại bằng E5 đã ghim có cosine gần 1 | [Mẫu embedding](embedding-samples.json) |
| Restore | Restore backup vào SQLite tạm riêng; toàn bộ ID/checksum chunk khớp snapshot | [Restore](restore.json) |
| Đối chứng âm cho helper | Bản sao tạm bị sửa một chunk được phát hiện và báo lỗi đúng; snapshot thật không đổi | [Negative control](negative-control.json) |
| PostgreSQL | 59 tài liệu, 7.555 chunk; ID/checksum/embedding model của mọi chunk khớp snapshot | [Metadata](production-metadata.json), [chunk integrity](postgresql-chunk-integrity.json) |
| Nguồn online mẫu | PDF đầu tiên của 5 nguồn kiểm tra đều HTTP 200 và khớp byte snapshot | [Live source samples](live-source-samples.json) |
| Giới hạn truy nguyên trang | 44 cảnh báo cùng thuộc NQ254/2025; không phải 44 văn bản hỏng | [Warnings](integrity.json) |
| Encoding/đoạn dư | Không có ký tự thay thế `�`; có 9 đoạn rất ngắn và 5 nhóm đoạn trùng cần xem xét trong ngữ cảnh | [Document findings](integrity.json) |

5 nguồn online mẫu là Luật Đất đai 2024, NĐ226/2025, QĐ40/2026 Hà Nội, NQ56/2022 và Luật Thủ đô 2026. Chỉ so sánh PDF đầu tiên, không kiểm tra mọi attachment hoặc mọi sửa đổi sau đó. Đây không phải rà soát pháp lý đầy đủ và không được dùng để tự gia hạn freshness của cả corpus.

### Retrieval trên hai backend

Chạy cùng model E5 ONNX Q8 thật và các suite đã khóa, dùng câu hỏi gốc, top 8; **không gọi generation**. Chỉ 20 ca có gold được đo trên mỗi backend; các ca không có gold không trở thành điểm retrieval. SQLite được restore riêng từ backup. PostgreSQL chỉ thực hiện đọc; không restore đè database dịch vụ.

| Suite | Ca có gold | SQLite: hit / Recall@8 | PostgreSQL: hit / Recall@8 |
|---|---:|---:|---:|
| Smoke | 11 | 9/11 · 81,82% | 9/11 · 81,82% |
| Supplemental | 3 | 3/3 · 100% | 3/3 · 100% |
| Natural | 6 | 5/6 · 75% | 5/6 · 75% |

Artifact: SQLite [smoke](sqlite/retrieval/smoke.json), [supplemental](sqlite/retrieval/supplemental.json), [natural](sqlite/retrieval/natural.json); PostgreSQL [smoke](postgresql/retrieval/smoke.json), [supplemental](postgresql/retrieval/supplemental.json), [natural](postgresql/retrieval/natural.json). [Log](retrieval-run.log) giữ kết quả của cả sáu phép đo.

Hai backend có cùng chỉ số trong mẫu này nhưng không được coi tương đương: thứ hạng/kết quả ngoài mẫu có thể khác. Fingerprint audit SQLite là `fb241ec45cc8c607e8e9c414531b877de3e50ec7d927a9bfb25eec53b984d5c7`; PostgreSQL là `3fbb34e479b86c4ca44ab8d3b2fbc7e861a0bfc8f372d4332d9c25274b0bb694`. Đây là cấu hình source local dùng để đo, không phải tuyên bố source mới đã deploy trên Render.

### Phân loại ca hụt retrieval

- **S13, N06:** thiếu điều khoản thay thế QĐ56 bằng QĐ40 trong top 8 dù gold chunk `qd-40-2026-hanoi-0-2-0` có trong corpus. Cần kiểm tra tìm kiếm số hiệu, câu không dấu và cách ưu tiên quan hệ thay thế hiện có; chưa có căn cứ rằng thêm bản sao văn bản sẽ sửa lỗi này.
- **S14:** câu “Văn bản đó…” phụ thuộc history. Phép đo query gốc cố ý không giải tham chiếu; kết quả 0 không chứng minh thiếu nguồn. Phải đánh giá nhánh context của agent riêng.
- **N03:** gold khóa gồm cả parent và child; child đã nằm trong top 8, parent không nằm trong kết quả search nên Recall@8 bằng 0,5. Giữ nguyên annotation; không sửa gold sau khi thấy kết quả để nâng điểm.

Các kết quả này đo khả năng tìm nguồn, không phải accuracy của đáp án agent. Luồng agent còn mở điều khoản và quan hệ pháp lý nên có thể khôi phục một số ca raw search hụt. Không chạy lại generation/judge trong lần kiểm tra corpus này; báo cáo model cũ không được đổi nhãn thành kết quả của commit mới.

## Các vấn đề cần xử lý

### 1. Độ mới nguồn sắp hết hạn

Tại thời điểm kiểm tra, `source_fresh=true`, bảng receipt production chưa có bản ghi. Mốc nhỏ nhất của snapshot là `2026-10-11T17:32:27Z`. Theo runtime hiện tại, nếu không có rà soát mới, freshness chung hết hạn vào **00:32:27 ngày 19/10/2026, giờ Việt Nam**. Đây là mốc tính từ snapshot, không phải xác nhận trạng thái sau thời điểm audit.

Cần rà soát nguồn, sửa đổi và chuyển tiếp rồi ghi receipt đúng checksum. Không tăng `checked_at` chỉ vì URL còn trả 200. [Status công khai](live-status.json) cho thấy generation còn available trong lần kiểm tra; `/readyz` gặp timeout và chưa được xác minh thành công trong attempt này.

### 2. Thiếu nguồn và graph pháp lý

Corpus khai báo 5 coverage gaps: QĐ10/2017, QĐ30/2019, QĐ20/2023 Hà Nội, NĐ123/2024 và NQ106/NQ-CP về Vành đai 4. Bốn unresolved relations còn yêu cầu thêm NĐ01/2017 và NĐ148/2020. Hợp hai danh sách có **7 nguồn thiếu khác nhau**, không phải mọi nguồn đều có mức ưu tiên như nhau.

Đề xuất bổ sung theo nhu cầu hồ sơ lịch sử và dự án: QĐ10/2017, các sửa đổi liên quan NĐ47/2014, NQ106; xử lý cặp bảng giá lịch sử QĐ30/QĐ20 khi cần tra cứu giai đoạn đó. NĐ123 về xử phạt nên ưu tiên sau các nguồn trực tiếp phục vụ bồi thường/hỗ trợ/tái định cư. [Trang Chính phủ của NQ106](https://vanban.chinhphu.vn/?pageid=27160&docid=206398) hiện có PDF chính thức; web reader nhận ra 9 trang nhưng không trích được text, phù hợp hướng OCR và rà soát thay vì coi nguồn không tồn tại.

**QĐ27/2024 hiện không có outgoing relation nào**, dù tiêu đề và toàn văn nguồn nói sửa QĐ10/2017. Cần đối chiếu điều khoản để khai báo đúng relation/source locator/target scope và chuỗi thay thế. Bổ sung văn bản mà không sửa graph vẫn để lại điểm mù này. Xem [diagnostics](diagnostics.json).

### 3. Truy nguyên trang và chất lượng layout

NQ254 được xử lý từ 15 ảnh nguồn chính thức thành PDF ghép phục vụ OCR, không phải PDF ký số gốc. Các chunk có page nhưng `source_files` không có URL attachment phù hợp, nên 44 chunk không tạo được liên kết tới đúng PDF/trang. Provenance ảnh và OCR vẫn có hash hợp lệ. Đề xuất giữ phân biệt này, bổ sung ánh xạ từng trang tới ảnh gốc và manifest; không dựng URL PDF ký số giả.

QD71/2024 còn các số hiệu bị layout tách như `7 1/2024`, `3 0/2019`, `2 0/2023` tại chunk `qd-71-2024-hanoi-0-0-0`. Parser tái lập đúng không chứng minh chuỗi số đã đọc tốt. Cần so ảnh gốc rồi chuẩn hóa có kiểm soát; không nối khoảng trắng trong mọi bảng vì có thể làm đổi giá trị/cột. Các cảnh báo PDF về trang xoay/whitespace cũng cần được đọc như giới hạn trích xuất, không phải xác minh số liệu.

9 đoạn ngắn chủ yếu là heading, publication header hoặc chữ ký; 5 nhóm trùng gồm cả điều khoản được lặp hợp pháp. Không xóa tự động chỉ vì trùng hoặc ngắn: giữ heading/context cần thiết cho child và chỉ gỡ đoạn không mang chứng cứ sau rà soát.

### 4. Phạm vi chỉ mục và checker cũ

Sáu luật chuyên ngành trong [diagnostics](diagnostics.json) chiếm 833 chunk (khoảng 11% corpus), trong khi các relation khai báo chỉ dẫn tới một số điều/khoản sửa luật đất đai/quy hoạch. Đây là ứng viên thu gọn chỉ mục, chưa phải 833 chunk được xác nhận vô ích. Giữ toàn văn raw, chỉ lọc sau khi rà đủ điều khoản sửa đổi, định nghĩa, hiệu lực và dẫn chiếu cần thiết; giữ nguyên embedding các chunk không đổi.

`ingest.coverage()` còn yêu cầu cả `ring4`, `songhong`, `olympic` đều có ít nhất 5 tài liệu nên báo `coverage_passed=false`, `publication_ready=false` với corpus Vành đai 4. Đây là checker cũ lệch phạm vi, không phải lý do thêm hai dự án đã loại bỏ. Cần sửa checker theo contract Vành đai 4 và coverage theo tác vụ/chuỗi nguồn; publication validator hiện tại là phép kiểm tra khác và đã đạt integrity.

## Phương án đề xuất

**Ưu tiên bản vá corpus có chọn lọc:**

1. Rà soát freshness và receipt; giữ generation tự chặn khi nguồn quá hạn.
2. Bổ sung nguồn thiếu có ưu tiên và hoàn thiện graph, đặc biệt relation QĐ27 → QĐ10; kiểm tra toàn văn, OCR, số liệu và hiệu lực trước khi đưa vào staging.
3. Sửa ánh xạ ảnh/trang, xử lý layout bị tách số và đoạn dư đã chứng minh; rà phạm vi chỉ mục của luật chuyên ngành. Không embedding lại phần giữ nguyên; chỉ embed chunk mới hoặc thực sự thay đổi bằng cùng contract E5.
4. Tạo snapshot mới có ID/checksum riêng. Đo lại cùng suite khóa và kiểm tra cả hai backend; đánh giá generation với review gắn checksum khi thay đổi liên quan. Đặt tiêu chí chấp nhận trước khi sửa, không đổi gold hoặc chọn attempt đẹp.
5. Restore vào database riêng, kiểm tra Release tải về và fingerprint rồi mới chuyển active. Giữ bản cũ có thể rollback đúng phạm vi; chỉ gỡ Release cũ sau phát hành và restore thành công.

**Chỉ xây lại corpus hoàn toàn** nếu một đợt kiểm tra chứng minh provenance không phục hồi được, sai OCR/locator có tính hệ thống hoặc nguồn không đủ điều kiện sử dụng. Lần này chưa có bằng chứng đó: 130 artifact khớp hash, 59 tài liệu tái lập được và các vector mẫu đúng contract. Ngay cả khi xây lại, vẫn giữ raw có xuất xứ, artifact/checksum lịch sử và triển khai snapshot mới song song; không drop database hoặc xóa bản đang phục vụ trước.

## Tái lập và giới hạn

Helper kiểm tra offline: [`scripts/audit_corpus.py`](../../scripts/audit_corpus.py). Dùng một output mới, không ghi đè báo cáo này:

```bash
.venv/bin/python scripts/audit_corpus.py \
  --snapshot data/releases/corpus-581da76c79b0b362.json \
  --output reports/<new-audit-directory>/integrity.json \
  --replay-parser
```

[reproduction/](reproduction/) giữ đúng các driver đã thực thi, gồm bản audit ở attempt đầu. Những driver một lần này có output directory cố định: đọc để tái lập, đổi output sang thư mục mới trước khi chạy; không ghi đè artifact lịch sử. `integrity-final-script.json` kiểm tra lại integrity bằng helper đã làm sạch lint, không chạy lại parser; đối chiếu replay tại `integrity.json` của attempt đầu. Mọi input/suite và artifact được ghi hash trong `checksums.json`.

SHA `e1db9ef` xác định runtime được đánh giá. Helper audit được tạo trong lần làm việc này; bản thực thi ban đầu được giữ tại `reproduction/audit.py`, bản helper cuối và các driver có checksum riêng. Không coi helper mới là file đã có trong commit runtime đó.

Không thay suite 20+4 và natural đã khóa. Không có model generation, legal judge hoặc thẩm định pháp lý độc lập; không khẳng định mọi số liệu OCR/bảng đã đúng chỉ từ checksum. PostgreSQL được so metadata chunk, không rehash toàn bộ text/vector vật lý. Không đo latency HTTPS hay hoàn tất public chat qua Turnstile. Các hạn chế đó không được coi là đã pass.
