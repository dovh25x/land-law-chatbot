# Giới hạn và threats to validity

Tài liệu này đi kèm [báo cáo](FINAL_PROJECT_REPORT.md), không phải danh sách chức năng sẽ tự triển khai. Các số thực nghiệm chỉ có ý nghĩa trong cohort/backend/ngày hỏi được nêu ở [evaluation summary](EVALUATION_SUMMARY.md).

## Giới hạn cần công bố

1. **Chưa xác nhận model trả lời thành công trên runtime cuối.** S06 giữ FAIL ở cohort cũ; C01 Phase 3A INCOMPLETE; C02/C03 NOT RUN. Không dùng fixture hoặc Recall@5 để quảng bá “độ chính xác chatbot 97,37%”.
2. **Phạm vi pháp lý hẹp và có ngày.** Chỉ Vành đai 4 tại Hà Nội và luật chung liên quan, trong các điều khoản/ngày đã review. Có 60 records nhưng không phải 60 văn bản đã xác minh hiện hành. Whole-document state 59 stale/1 unknown và scoped gate là hai cấp khác nhau. Receipt ngày 21/10/2026 không tự xác nhận ngày 23/10/2026.
3. **Không kết luận quyền lợi cá nhân.** Cần loại đất, nguồn gốc, giấy tờ, ngày quyết định/phương án và chuyển tiếp. Không suy “có sổ đỏ” là đủ cho mọi nhóm; không tính tiền, suất tái định cư hoặc xác định thửa.
4. **Nguồn ngoài phạm vi có thể làm lượt từ chối.** Fail-closed là chủ đích, nhưng chưa có False Abstention Rate model trên tập answerable độc lập. Không tuyên bố mọi refusal là thành công an toàn.
5. **Cloud chưa được nghiệm thu với tuple mới.** Local image/PG nếu đạt chỉ chứng minh môi trường đó. Signed ingress, Turnstile, Render cold start, quota thật và public E2E phải xác minh riêng sau phê duyệt. Không coi file cấu hình hoặc fixture browser là production pass.
6. **Ngân sách có khoản unknown.** Provider không xác nhận usage của hai lỗi. Không tự thu hồi reservation cũ, reset allocation hoặc gán upper bound thành tokens thực tiêu thụ. Allocation cũ không đủ cho C02 precheck.
7. **Reproducibility cần giao asset.** Clone source không tự có staging corpus/model bị ignore. Cần checksum, receipt bundle, script và phương thức giao asset phù hợp; không đưa `.env`, credentials hoặc dữ liệu người dùng vào gói nộp.
8. **Thông tin học phần chưa có.** Bìa để trống theo yêu cầu; chưa đối chiếu syllabus/rubric, chưa có PDF/slides chính thức hoặc xác nhận điểm chuẩn học thuật.

## Bảng threats to validity

| Nhóm | Rủi ro | Hệ quả | Cách trình bày/giảm rủi ro còn khả thi |
|---|---|---|---|
| Construct | Recall đo ID tìm được, không đo luật đúng | Nhầm retrieval với answer correctness | Công bố macro/micro/IDs; tách layer và metrics chưa đo |
| Construct | Citation integrity khác entailment | Citation đúng URL nhưng claim sai phạm vi | Review subject/condition/exception/time ở cặp claim–citation |
| Construct | Refusal làm giảm số claim để chấm | Có thể tạo faithfulness cao nhưng ít giúp người dùng | Báo answerable denominator, false abstention và coverage cùng correctness |
| Internal | Tác giả vừa xây code vừa review gold/source | Confirmation bias và label leakage | Giữ gold khóa, lưu hash; đề nghị giảng viên/người review độc lập, chưa thực hiện |
| Internal | Nhiều vòng sửa cùng case | Overfit S06/C01 và fixture | Dừng tối ưu theo quyết định; giữ mọi failure, không chọn best attempt |
| Internal | Provider 429/400 và budget dừng | Censoring không ngẫu nhiên | Báo INCOMPLETE, raw receipts và request count; không loại khỏi báo cáo |
| Internal | Cùng model sinh và judge ở lịch sử | Judge bias/correlated errors | Ghi rõ evaluator tùy biến, chưa có human legal accuracy final |
| Internal | Context C03 6.981/7.000 ký tự | Thay serialize/selection có thể mất đoạn | Khóa fingerprint và actual payload; không chỉ kiểm intermediate retrieval |
| External | 19 câu có gold, tác giả chọn | Không đại diện toàn bộ câu hỏi người dân | Báo 19/32 và exclusions; không suy production accuracy |
| External | SQLite khác PG/pgvector | Ranking, SQL và concurrency khác | Báo backend riêng; local PG không thay benchmark trên cloud |
| External | Ngày hỏi lịch sử và hiện hành trộn trong retrieval | Không chứng minh toàn tập current | Công bố `as_of` từng dòng và review scope |
| External | Chưa có usability study với người dân | UI fixture pass không đo dễ hiểu/dễ dùng | Giới hạn tuyên bố UX ở implementation; chưa báo satisfaction |
| Conclusion | Mẫu model rất nhỏ/chưa hoàn tất | Không có estimate đáng tin cho accuracy/p95 | NOT MEASURED; không tự thêm confidence interval từ số liệu không phù hợp |
| Conclusion | Nhiều fingerprints/corpus | Gộp tạo score giả | Cohort ledger và evidence hashes, không tính trung bình chung |
| Reproducibility | Dependencies/container tags có phần mutable | Build tương lai có thể khác | Lock packages, ghi image ID/digest thực; không gọi base tag là immutable |
| Legal | Snapshot/receipt là review kỹ thuật có giới hạn | Có thể bỏ sót sửa đổi hoặc chuyển tiếp | Liên kết nguồn chính thức và phạm vi; không coi receipt là chứng nhận pháp lý độc lập |
| Privacy | Model provider nhận query/context | Không thể cam kết toàn bộ xử lý trên thiết bị | Chỉ dùng câu giả lập; không nhập PII; account retention/ZDR chưa xác minh |

## Nội dung nên đọc rõ trong buổi bảo vệ

“97,37% là macro Recall@5 trên 19 câu có gold, chạy SQLite; không phải độ chính xác đáp án. Model pilot chưa hoàn tất, và candidate cuối chưa có lượt trả lời RAG được xác nhận. Em trình diễn nguồn, retrieval và guard đã kiểm chứng; các phần cloud/model chưa nghiệm thu được ghi riêng.”

Đề xuất thông báo UI trước khi phát hành: phạm vi Vành đai 4 Hà Nội; ngày/phiên bản nguồn được dùng; không nhập PII; câu trả lời không quyết định hồ sơ hoặc quyền lợi. Phase 4 chỉ ghi yêu cầu vào tài liệu, không tự đổi giao diện hay hành vi runtime.
