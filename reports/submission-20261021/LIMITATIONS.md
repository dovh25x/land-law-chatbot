# Giới hạn công bố của bản bàn giao

## Sản phẩm hiện tại

Candidate chỉ **tra cứu đoạn nguyên văn đã review** (`SOURCE_LOOKUP_ONLY=true`, `GENERATION_ENABLED=false`). Không sinh đáp án pháp luật, xác định thửa đất, tính tiền hoặc cam kết quyền lợi/suất tái định cư. Pipeline RAG giữ trong source, nhưng chưa có legal-answer PASS được xác nhận từ model trên candidate nghiên cứu cuối.

Code ec5d9a9… đã có CI PASS và được deploy với API identity khớp; [public browser source-only](../release-final-20261021/qa/public-source-2026-10-21T11-02-32-079Z/report.json) đã PASS trên desktop 1440px/mobile emulation 390px, 0 model/session. Public source lookup không đồng nghĩa human Turnstile, chat/follow-up generative hoặc full system E2E đã đạt. Các chức năng đó bị tắt/không kiểm trong mode hiện tại.

## Phạm vi pháp luật và ngày

- Chỉ Vành đai 4 tại Hà Nội và luật chung liên quan, trong đúng phần/nhánh đã review; không bao phủ mọi dự án hoặc cơ chế đặc thù.
- 60 document records/7.396 chunks là snapshot, không phải 60 văn bản fresh. API hiện43 passages cho 21/10/2026; ngày 22–23 chỉ một header QĐ 40, không đủ nghiệp vụ. Historical02/08/2024 có 25 passages.
- Có thể chọn rõ21/10/2026 làm **historical as_of** vào ngày 22/23; không gọi đó là coverage hiện hành ngày 23. Release này không bổ sung coverage mới cho 22/23.
- Archived receipts chứng nhận scope/thời điểm đã review, không evergreen freshness. Live import yêu cầu review gần đây không quá 7 ngày. Restore byte/checksum có thể PASS nhưng activation sau expiry cần renewed review hợp lệ; không sửa `checked_at`, tự gia hạn hoặc bypass F01.
- Hiện nguyên văn/locator không xác nhận mọi điều kiện hoặc quyền lợi của một hộ. Review kỹ thuật chưa phải thẩm định pháp lý độc lập; cần hồ sơ và cơ quan có thẩm quyền khi áp dụng cá nhân.

## Chất lượng model và metrics

S06 giữ **FAIL**; C01 **INCOMPLETE**; C02/C03 **NOT RUN trong Phase 3A**. C02 allocation độc lập mới **INCOMPLETE** (HTTP400 JSON truncate, không published answer). Không dùng fixture hoặc macro Recall@5 **97,37% trên 19 câu SQLite** để quảng bá chatbot “chính xác 97,37%”.

RAGAS chưa chạy. Answer Correctness, semantic Citation Accuracy, final-model Faithfulness, Answerable Coverage/False Abstention Rate và model/public p50/p95 trên bộ đủ mẫu chưa đo. Source-only có 0 model claims không đồng nghĩa faithfulness hoặc correctness bằng 100%. Recall thuộc fingerprint1697…, API source-only thuộc dba69995…/8ee1cd63…; không gộp các cohorts.

Mẫu do tác giả chọn nhỏ, nhiều vòng sửa trên cùng tập, thiếu holdout/người gán nhãn độc lập và khác biệt SQLite/PostgreSQL. Historical custom faithfulness dùng cùng model làm judge, không phải independent legal certification hoặc RAGAS.

## UX, reliability và privacy

Public browser đã phát hiện race history trước metadata; failure artifacts giữ nguyên. Guard cuối khóa citation/structured actions/panels và chat khi runtime chưa biết/lỗi, cảnh báo lịch sử chưa review lại. Frontend CI fixtures không tự thay actual public browser acceptance của guard đã deploy.

Hosting Free có cold start, quota và source/status GET có thể chậm; image memory probe dưới 512 MiB không phải public load test. Không có server replay đáp án. History chỉ lưu IndexedDB 7 ngày trên thiết bị, không đồng bộ tài khoản; mất/xóa dữ liệu thiết bị không phục hồi từ server.

Không nhập PII/hồ sơ thật. Khi đọc website/click nguồn, network metadata vẫn tới các dịch vụ; không tuyên bố mọi dữ liệu chỉ ở thiết bị. Provider Zero Data Retention chưa xác minh, dù source-only hiện không gọi model. API model cũ có usage unknown; upper bound/reservation không phải tokens đã đo và không được tự refund.

## Tái lập và tài liệu

Cần code SHA, locks, corpus/model assets có checksum, scoped receipts và context/attempt artifacts. Clone source không tự có assets bị ignore. Không giao `.env`, credentials, database local hoặc production backup trong ZIP học thuật. Source-only PG API PASS là GET/read-only, không PG Recall hoặc full pytest trên PostgreSQL.

Bìa/học phần/MSSV/GVHD để trống theo yêu cầu; rubric chưa được cung cấp. PDF/PPTX đã xuất không xác nhận đáp ứng một mẫu chấm chưa có. PPTX editable chưa render bằng Microsoft PowerPoint/LibreOffice trên môi trường này; PDF slide được render từ cùng source và nhúng font để dự phòng. Các links trong PDF trỏ stable GitHub tag/Release assets thay local file; cần công bố đúng tag sau khi tạo assets.
