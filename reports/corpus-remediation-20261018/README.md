# Triển khai remediation corpus — 18/10/2026

**Chưa đủ điều kiện phát hành hoặc deploy.** Bản sửa kỹ thuật được commit tại `e778240`; corpus ứng viên là `corpus-caf3c0833096ea4e`. Corpus đang phục vụ vẫn là `corpus-581da76c79b0b362`. Không ghi serving DB, đổi active, phát hành Release hoặc xóa Release cũ. Đây là kiểm tra kỹ thuật có rà rubric/đoạn nguồn bởi AI, không phải thẩm định pháp lý độc lập.

[PLAN.md](PLAN.md) khóa tiêu chí trước thay đổi. [acceptance-status.json](acceptance-status.json) ghi các cổng còn chặn. [runtime-source.json](runtime-source.json) ghi SHA runtime, fingerprint, suite và checksum candidate.

## Các thay đổi đã triển khai

- Retrieval giữ nhánh tìm đúng số hiệu cả khi không chỉ rõ điều; câu hỏi hiệu lực/thay thế/bãi bỏ lấy thêm các đoạn điều khoản thay thế từ relation đã xác minh. Giới hạn số ứng viên, lọc thời điểm và phạm vi nguồn; không thêm LLM, tool, retrieval round hoặc reranker.
- NQ254 có ánh xạ 15 trang sang ảnh gốc cùng SHA-256. Citation mở ảnh gốc hoặc trang PDF đã xác minh; frontend dùng nhãn “Mở trang nguồn gốc”, không nhận PDF ghép là PDF ký số.
- QĐ71 chỉ sửa sáu lần tách khoảng trắng của ba số hiệu văn bản đã đối chiếu; không nối hoặc đổi giá trị bảng. Năm chunk đổi checksum được embed bằng đúng E5 contract, các chunk không đổi giữ nguyên từng phần tử vector.
- Chỉ mục Luật 71/2025 giữ Điều 1–3, 49–50; Luật 116/2025 giữ Điều 1–3, 43–45. Giữ toàn văn raw và toàn bộ điều sửa đổi/định nghĩa/hiệu lực/chuyển tiếp trong phạm vi đã chọn. Tổng cộng bỏ 167 chunk khỏi chỉ mục. Bốn luật chuyên ngành còn lại giữ nguyên vì lựa chọn ban đầu chưa chứng minh đủ phụ thuộc; lý do tại [projection-candidates.json](projection-candidates.json).
- Khai báo QĐ27 → QĐ10 với scope sửa/bãi bỏ từng khoản, cùng quan hệ bãi bỏ QĐ20/2022. Endpoint chưa duyệt vẫn để unresolved, không suy quan hệ một phần thành bãi bỏ toàn văn.
- Checker chỉ kiểm tra phạm vi Vành đai 4, nguồn bắt buộc và chứng cứ dự án đã duyệt. Publication còn bị chặn bởi gap, dependency chưa giải quyết, ingest issue, embedding/metadata thiếu. CLI `publish` kiểm tra coverage và freshness trước backup/activation.
- Hỗ trợ OCR theo một phần PDF với `page_numbers` vật lý có kiểm tra thứ tự, phạm vi, trùng và biên bản scope. OCR chưa rà soát bị quarantine.
- Kiểm thử model phát hiện khái quát sai danh mục hỗ trợ. Guard mới chặn nghĩa vụ áp dụng mọi khoản, số nhóm khép kín không khớp danh mục nguồn và việc biến hợp đồng giao khoán thành điều kiện chung. `finish` bỏ đoạn giới hạn tự nối sau verify. Ví dụ không khép kín vẫn được phép; không nới verifier để tăng điểm.
- Helper chuẩn bị candidate, restore/đo hai backend và packager giữ báo cáo/output riêng; packager từ chối ghi đè artifact. Không đổi model, embedding contract, hosting Free, pipeline hoặc các ngân sách mỗi lượt.

## Bằng chứng corpus và retrieval

Candidate có 59 tài liệu, 7.388 chunk; giữ chính xác vector của 7.383 chunk, chỉ năm chunk khác nội dung so baseline. Hai lần chuẩn bị tái lập cùng ID và cùng SHA-256 `845bef1d3928d41fc5e694f5747a311f87f9c42591b3b516554196ce66bc8149`.

[Integrity có parser replay](integrity-attempt-1.json) và [kiểm tra manifest cuối](integrity-final.json): 0 lỗi, 0 cảnh báo; mọi gold chunk của ba suite được giữ. Không thay suite 20+4 hoặc natural 8 ca. Integrity/checksum không chứng minh OCR và diễn giải pháp lý đúng.

| Backend | Suite | Baseline raw Recall@8 | Candidate raw Recall@8 |
|---|---|---:|---:|
| SQLite | smoke, 11 ca có gold | 9/11 | 10/11 |
| PostgreSQL riêng | smoke, 11 ca có gold | 9/11 | 10/11 |
| SQLite | supplemental, 3 ca có gold | 3/3 | 3/3 |
| PostgreSQL riêng | supplemental, 3 ca có gold | 3/3 | 3/3 |
| SQLite | natural, 6 ca có gold | 0,75 | 0,9167 |
| PostgreSQL riêng | natural, 6 ca có gold | 0,75 | 0,9167 |

[Hai backend](evaluation-attempt-1/) được restore riêng và đối chiếu chính xác documents/relations. S13 và N06 phục hồi gold. S14 raw query vẫn không có history; không sửa annotation N03 parent/child để tăng điểm. Retrieval đã đo trước guard hỗ trợ cuối; [hash engine](runtime-source.json) xác minh Store, provider, embedding, retrieval và config giữ nguyên. Không coi số đo này là generation hay legal accuracy.

[Runtime role PostgreSQL](postgres-runtime-role.json) đạt: chỉ DB mới của lần kiểm tra được tạo/xóa; phục vụ không bị migrate hoặc ghi. Đã kiểm tra runtime role, session lease đồng thời và quyền ghi hội thoại bị thu hồi.

## Nguồn mới và freshness còn chặn

Đã tải lại 64 nguồn trong manifest ban đầu; 67 attachment tải được đều khớp hash bản đã lưu. Đây là so byte, không phải review sửa đổi/chuyển tiếp. [Bundle rà soát](source-review-bundle.json) giữ tham chiếu raw/locator/URL liên quan và template chưa có verdict, thời điểm hoặc xác nhận; không có receipt giả được ghi.

Đã lấy thêm [PDF gốc QĐ56/2024 từ publication hiện tại](qd56-current-original.log), 15 trang, để đối chiếu với HTML cache cũ; chưa dùng việc tải được PDF thay cho receipt sửa đổi/chuyển tiếp.

Đã phục hồi PDF và tạo OCR ứng viên cho bảy nguồn ban đầu: QĐ10/2017, QĐ30/2019, QĐ20/2023, NĐ123/2024, NQ106/2022, NĐ01/2017 và NĐ148/2020. Tất cả giữ `pending`. OCR có lỗi thực tế: NQ106 đọc ngày 18 thành 48 và số 56 thành 36; QĐ20/2023 có trang gần trống và bảng cần đối chiếu; QĐ20/2022 đọc sai ngày và năm trong phần căn cứ. Không tự sửa số bằng suy đoán hoặc nhận confidence OCR là đủ.

Link `p_steering=188741` người dùng gửi mở NQ20/2023/NQ-HĐND về ngân sách. Bản scan đúng QĐ20/2023 đã tìm thấy tại [kho archive Hà Nội](https://storage-vnportal.vnpt.vn/gov-hni/CrawlDownloads/vanban-hanoi-gov-vn/documents/10182/2518750/QDPQ-20-2023.pdf), SHA-256 `a4b48290f866ac0b4d13f64de6a6a7d276f992373bb8f0e4a542bc8a52d7784a`, 58 trang. Đã đối chiếu trang đầu đúng số, ngày và nội dung; chưa duyệt publication link hiện hành, OCR toàn văn hoặc chuỗi pháp lý. [Log tải](qd20-direct-candidates.log), [OCR quality](qd20-ocr-quality.json).

Còn phát hiện QĐ20/2022 trong Điều 2 QĐ27; [ứng viên scan ba trang](additional-endpoint-candidate.json) đã tải, chưa đưa vào serving manifest hoặc gán endpoint đã giải quyết. Cần rà scope sửa khoản 2 Điều 26, ngày hiệu lực, dẫn chiếu Điều 7 và việc bị QĐ27 bãi bỏ.

[Kiểm tra serving lúc 17:32 UTC](serving-status.json): corpus cũ vẫn active, có 0 source-review receipt và `source_fresh=false`. Không tăng `checked_at` để mở generation. Câu hỏi lịch sử trong bộ khóa không chứng minh hệ thống đủ freshness cho câu hỏi hiện hành.

## Generation và quyết định phát hành

Lượt đầu chạy đủ 20+4+8 ca, mọi attempt/model output và lỗi quota được giữ tại [generation-attempt-1/](generation-attempt-1/), [log](generation-attempt-1.log). Đây là fingerprint `ce30e830…`, trước guard hỗ trợ cuối, được giữ làm bằng chứng phát hiện lỗi.

Review gắn checksum: [smoke](reviewed/smoke/evaluation.json) 18 pass, 1 partial, 1 fail; [supplemental](reviewed-attempt-1/supplemental/evaluation.json) 2 pass, 2 fail; [natural](reviewed-attempt-1/natural/evaluation.json) 4 pass/8, trong đó chỉ 2/6 câu nội dung đạt. N04 tiêu hết sáu request bởi quota/retry; giữ trong mẫu. N02/N03/N06 abstain không được tính là pass chỉ vì an toàn. X02 dẫn tới bản vá guard; S08 còn câu mở đầu quá rộng. Không tuyên bố đạt mục tiêu natural >=5/6.

Lượt thứ hai dùng fingerprint cuối `817e3825…`, cùng suite và candidate, nằm tại [generation-attempt-2/](generation-attempt-2/) cùng [log](generation-attempt-2.log). [Review cuối](reviewed-final/) gắn checksum: smoke 19 pass/20, supplemental 2 pass/4; natural 4 pass, 1 partial, 3 fail/8. Chỉ 2/6 câu nội dung đạt đầy đủ; N06 đạt một phần do thiếu lưu ý hồ sơ cũ. N02/N04 abstain không được tính pass; N03 vẫn `limited`. Tổng cộng đã thực thi đủ **32/32 ca**, còn một ca lỗi thực thi; không đạt mục tiêu natural >=5/6.

Người dùng đã cập nhật Groq key hai lần trong quá trình tiếp tục. [Probe key mới nhất](updated-key-probe-2.json) trả HTTP 200, 611 token, nhưng header vẫn giới hạn 8.000 token/phút. [Resume đầu](natural-resume-user-configured-key.log) giữ N01/N03/N06 limited; [resume key mới nhất](natural-resume-user-configured-key-2.log) giúp N01/N06 trả lời, N03 vẫn limited sau sáu request. Vẫn có phản hồi TPM và một lỗi JSON schema được retry trong ngân sách. Đây là kết quả thực thi quan sát được, không chứng minh key mới tăng hạn mức hoặc bảo đảm throughput. Cần phân biệt cải thiện thực thi với mức đúng nội dung.

N07/N08 được chạy riêng qua nhánh tất định với provider bị khóa và xác minh 0 request ([bằng chứng](deterministic-remainder.json)). [Bản review trước khi cập nhật key](reviewed-before-user-key/natural/) cùng mọi attempt/model output được giữ nguyên. Không trộn hai fingerprint hoặc chọn ca đẹp từ lượt khác. Export review cuối dùng cùng cấu hình SQLite tạm như CLI; không so fingerprint với PostgreSQL mặc định của môi trường. [Kiểm tra phạm vi payload](generation-disclosure-check.json) xác nhận ba ca tiếp tục không chứa history người dùng và chỉ dùng corpus nguồn công khai.

[Helper tiếp tục](../../scripts/evaluate_generation_candidate.py) giữ checkpoint và kiểm tra `operator-cooldown.json` trước request. Chỉ tiếp tục khi provider có quota; hết `Retry-After` không bảo đảm đủ token cho cả lượt/suite. Người dùng đã cập nhật key và yêu cầu tiếp tục; lượt resume dùng cấu hình đó, giữ model/gói Free và tuân thủ giới hạn thực tế của Groq. Ví dụ tiếp tục các ca còn thiếu trên đúng runtime đã ghi fingerprint:

```bash
PYTHONPATH=backend .venv/bin/python scripts/evaluate_generation_candidate.py \
  --backup data/staging/remediation-20261018-attempt-1/candidate-backup.json \
  --output reports/corpus-remediation-20261018/generation-attempt-2 \
  --resume --split natural
```

[Negative control](resume-cooldown-negative-control.json) xác minh helper không mở cả backup khi cooldown chưa hết và gửi 0 generation request. Không công bố model acceptance khi chưa đạt tiêu chí nội dung của bộ khóa.

Chưa có thẩm định pháp lý độc lập hoặc faithfulness judge mới. Không phát hành chỉ từ unit pass, source-span match, citation integrity hoặc raw recall. Cần duyệt OCR/metadata/chuỗi pháp lý các nguồn mới, rà freshness có receipt thật, giải quyết gap/endpoint và đạt các tiêu chí model đã khóa trước activation.

[Package local theo SHA runtime cuối](package-final-source-preparation.json) đã chuẩn bị với working tree dirty được ghi rõ (các báo cáo đang hoàn thiện). [Hash local cuối](local-package-final-verification.json) khớp, backup trong package giống đúng bytes input đã restore trên hai backend. Package/receipt chuẩn bị trước đó vẫn giữ nguyên để truy nguyên. Chưa có tải lại asset từ GitHub Release; chưa xác nhận Release, deploy SHA/fingerprint hoặc public HTTPS chat. Giữ nguyên Release cũ và database phục vụ. Không có bằng chứng yêu cầu xóa và tạo lại toàn bộ corpus.

## Kiểm tra phần mềm và tái lập

- Backend cuối: [214 passed](backend-assistance-final-3.log). Các attempt lỗi cũ giữ nguyên, gồm test cũ yêu cầu đoạn nối sau verify đã được cập nhật theo contract.
- Frontend: [5 tests](frontend-unit.log), [build](frontend-build.log), [68 E2E](frontend-e2e.log). Screenshot lịch sử bị test ghi lại đã được khôi phục đúng bytes trước lần chạy.
- Secret scan: [kết quả](secrets-final-3.log). Lint ba helper candidate/generation mới: [kết quả](helper-lint-final-all.log); các lần quét rộng hơn có finding chưa xử lý tại [log](lint-attempt-1.log) và [log helper mở rộng](helper-lint-attempt-2.log), không được gọi là pass.
- [reproduction/](reproduction/) giữ driver một lần và cảnh báo output cố định. Helper duy trì ở `scripts/`, gồm lệnh tiếp tục generation trong SQLite tạm; dùng output mới khi tái lập. Tesseract portable chỉ dùng offline, không đổi dependency/runtime triển khai.

[Danh mục checksum](artifact-checksums.json) khóa các bằng chứng và input để truy nguyên.

Các diagram trước đó không đổi; bản vá giữ cùng graph node/edge và tăng điều kiện verify/publish. Không tạo diagram bằng công cụ khác `diagram-design`.
