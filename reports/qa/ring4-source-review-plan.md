# Kế hoạch review nguồn cho các khoảng trống Ring Road 4

- **Trạng thái:** đề xuất read-only, **chưa tạo receipt, chưa đổi policy, chưa mở production DB**.
- **Ngày lập:** 22/10/2026.
- **Căn cứ:** `reports/qa/ring4-corpus-quality.md`, `reports/qa/ring4-coverage-matrix.json`, `reports/qa/phase-a-two-turn-diagnosis.json`.
- **Hiện trạng:** 10/60 tài liệu có receipt đang pin; 74 đoạn reviewed; 43 đoạn admitted ngày 22/10/2026.
- **Nguyên tắc:** không suy hiệu lực từ PDF không đổi; không tự chuyển đoạn từ cửa sổ lịch sử sang standing nếu chưa đọc điều/khoản và quan hệ sửa đổi; mọi candidate mới phải giữ receipt cohort cũ.

## 1. Việc đã làm trong đợt này (deterministic)

- Sửa retrieval để đoạn đã review không bị top-K của tài liệu chưa review lấn át.
- Thêm guard citation/reference: đúng điều, khoản, số hiệu văn bản; chặn điều kiện thủ tục thêm vào không có trong nguồn; chặn nguồn tin/dự án chứng minh quyền lợi.
- Sửa lỗi evaluator L05 với cụm phủ định “đủ chắc chắn”.
- Không thêm tài liệu, không tạo receipt, không đổi policy, không xoá bất kỳ nguồn nào.

## 2. Worklist ưu tiên

| Ưu tiên | Tài liệu | Điều/khoản cần review | Hiện trạng | Vì sao cần | Kiểm tra bắt buộc |
|---|---|---|---|---|---|
| 1 | `luat-dat-dai-2024` | Điều 95 khoản 1–2; Điều 98; Điều 104; Điều 107; Điều 108; Điều 111 khoản 4 | 8 đoạn standing; Điều 104/107/94 nằm ngoài cửa sổ 2024-08-01→2025-01-01 | L01/L02/T01/T02 cần đúng điều kiện, hình thức bồi thường, hỗ trợ và tái định cư | Đọc bản Công báo; đối chiếu Luật 43/2024, Nghị quyết 254/2025, Luật 146/2025, Luật 84/2025; xác định target locators và hiệu lực từng khoản |
| 1 | `luat-nha-o-2023` | Điều 72 (bố trí nhà ở tái định cư/chỗ ở tạm thời) | Chưa có receipt | T01 hỏi chỗ ở mới/tái định cư; hiện bị loại vì chưa review | Xác minh Điều 72 còn hiệu lực; quan hệ với Luật Đất đai Điều 111; sửa đổi bởi Luật 43/2024 nếu có |
| 1 | `nd-88-2024` | Điều 11, 19, 30, 31 | Điều 11 standing; 19/30/31 ngoài cửa sổ 2024-08-01→2025-07-01 | Tái định cư, hỗ trợ, trình tự | Đối chiếu NĐ 226/2025 và NĐ 49/2026; đọc điểm bị bãi bỏ/sửa |
| 2 | `nq-254-2025` | Điều 3, 5–11, 13 khoản 3 | 12 đoạn standing; `target_locators` chưa đầy đủ | Cơ chế đặc thù có thể override Luật Đất đai cho dự án | Đọc toàn văn Nghị quyết; lập bảng override cho từng khoản; không suy từ tên dự án |
| 2 | `qd-40-2026-hanoi` | Điều 17, 21 và các điều liên quan | 8 đoạn standing; 1 đoạn trong legal window đến 2026-10-28 | Quy định Hà Nội đang áp dụng | Đối chiếu QĐ 56/2024, QĐ 38/2025, QĐ 10/2026; xác nhận phạm vi thay thế và điều chuyển tiếp |
| 2 | `luat-quy-hoach-2025` | Điều khoản phân biệt quy hoạch với thu hồi | Chưa có receipt | T01 hỏi “diện quy hoạch” | Xác minh hiệu lực 01/03/2026; quan hệ với Luật Quy hoạch 2017; không suy quy hoạch = thu hồi |
| 3 | `luat-khieu-nai-2011`, `nd-124-2020`, `luat-136-2025` | Trình tự, thời hạn, thẩm quyền khiếu nại | Chưa có receipt | C05/C11 | Xác minh hiệu lực và sửa đổi; tách khỏi nguồn vận hành |
| 3 | `nd-151-2025` | Điều khoản thẩm quyền còn hiệu lực | Có receipt nhưng ngoài cửa sổ 2025-07-01→2025-08-15 | C06 | Đối chiếu NĐ 49/2026 (bãi bỏ điểm đ, e) và NĐ 226/2025 (sửa Điều 6) |
| 3 | `ring4-nq56-2022` + 4 `official_news` | Phạm vi dự án, tiến độ, địa bàn | Chưa có receipt | C09; chỉ là context | Nếu review: ghi `source_kind=official_news/project_decision`, không dùng để chứng minh quyền lợi; cần guard claim-kind trước khi admission |
| 4 | Nguồn vận hành | Đầu mối tiếp dân, lịch tiếp nhận, biểu mẫu, thời hạn | Chưa có trong release | C07/C12 | Chỉ nhận nguồn chính thức của Hà Nội; ghi URL, ngày, phạm vi |

## 3. Quy trình candidate an toàn

1. Đọc văn bản gốc và ghi `verified_scope` mới với `as_of_from/as_of_to` đúng, không dùng standing cho điều còn phụ thuộc văn bản chưa đọc.
2. Chạy `scripts/build_standing_candidate.py` hoặc `scripts/prepare_current_legal_candidate.py` để tạo candidate **không ghi production**.
3. Chạy `scripts/audit_corpus.py`, `scripts/audit_citizen_coverage.py`, `scripts/evaluate_ring4_retrieval.py` và `scripts/verify_source_gate_candidate.py` trên candidate.
4. Kiểm tra boundary ngày, rollback về policy hiện hành, và bảo đảm mọi receipt cũ vẫn reachable.
5. Chỉ kích hoạt sau phê duyệt riêng; giữ nguyên release/policy đang chạy để rollback.

## 4. Giới hạn của kế hoạch

- Đây là worklist kỹ thuật, không phải kết luận pháp lý.
- Chưa có receipt mới; số đoạn admitted vẫn là 43 cho đến khi candidate được duyệt và kích hoạt.
- Các văn bản lịch sử (`luat-dat-dai-2013`, `nd-47-2014`, `qd-56-2024-hanoi`, ...) vẫn được giữ cho câu hỏi chuyển tiếp, không xoá.
