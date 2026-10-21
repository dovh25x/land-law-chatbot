# Pilot và demo — đề xuất, chưa được phép gọi model

Mốc pháp luật:21/10/2026. Dùng nguyên câu hỏi C01/C02/C03 và dữ kiện trong `acceptance-cases-final.json`; không bỏ điều kiện để làm câu trả lời dễ hơn. Bảng nguồn/đáp án kỳ vọng ở `LEGAL_REVIEW.md`. Nếu local acceptance của một ca còn fail, giữ ca đó fail và chưa coi pilot sẵn sàng chạy; không chọn ba câu khác để thay kết quả.

## Ba câu hỏi demo

1. C01: Hộ giả lập có GCN hợp lệ, sử dụng đất ở không thuê trả tiền hằng năm, sở hữu nhà gắn liền QSDĐ; thu hồi công cộng cho Vành đai4, không loại trừ/không phương án cũ. Giải thích điều kiện bồi thường và hình thức. Kỳ vọng:95(1a)+(2a),98(1), loại trừ254:3(10); không OR thành AND hoặc xác nhận quyền lợi cá nhân.
2. C02: Hộ giả lập sử dụng đất nông nghiệp đủ điều kiện bồi thường, mất40% cùng xã theo dự án hiện tại, không cộng dồn, không di chuyển, không phương án cũ. Hỏi nhóm hỗ trợ và nhánh đời sống tại40:17. Kỳ vọng:108(1),40:17(1a/b); nêu nhánh6tháng, không tính tiền hoặc mặc định mọi khoản/mọi nhân khẩu đều hưởng.
3. C03: Hộ ở xã, đủ95, nhà gắn QSDĐ, thu hồi hết, phải di chuyển, không còn nhà/đất ở khác cùng xã; không nhà nhà nước/chế độ đặc thù/phương án cũ. Kỳ vọng:88:11(2a),226:7(2a) đúng gạch thứ5,49:16(3g) về phần bãi bỏ,111(4),40:21; phân biệt xã/phường, giữ giới hạn diện tích/quỹ đất, không bảo đảm một suất.

Đây là demo có dữ kiện giả lập rõ ràng. Không dùng kết quả để quyết định quyền của hộ dân thật. Các câu thiếu loại đất/giấy tờ/ngày phương án/nhà khác cần hỏi bổ sung; dự án ngoài Vành đai4 hoặc nguồn chưa duyệt phải giới hạn/từ chối.

## Pilot model ngắn sau approval riêng

**Hiện chưa khuyến nghị chạy pilot3ca.** Review projection cuối cho thấy synthesis thiếu nguồn ởC01/C03, dù nguồn đã có trong retrieval và fixture raw-ID được guard chấp nhận. Cần khép blocker model-input và regressionharness trước, giữ các ca fail/expectedanswer. C02 có nội dung qua parent nhưng cũng chưa có modelpass. Không thayC01/C03 bằng câu dễ để công bố đạt3nhóm.

- Một attempt cho từng C01/C02/C03, tuần tự, SQLite riêng; không gửi toàn corpus, credentials hoặc PII. Dùng context công khai thực sự được retrieval chọn. Giữ snapshot, policy, mã runtime, model và prompt đúng manifest.
- Tối đa6HTTP request/ca tính retry,1repair,12tools,2retrieval rounds,90giây/ca; tổng tối đa18generation requests, không chạy lại ca fail để chọn kết quả đẹp. Dừng khi cooldown/quota yêu cầu. Runtime hiện không có hard token cap cho tổng pilot; không được mô tả dự toán dưới đây là giới hạn kỹ thuật đã thực thi.
- Dự toán36–45nghìn tokens cho3ca dựa trên trace hiện có, không phải benchmark đo được của3ca. Dành trước45nghìn từ ngân sách generation150nghìn đã đề xuất trong Phase2B, còn105nghìn; ngân sách đó cũng chưa được phê duyệt. Nếu usage thực tế hoặc request dự kiến vượt phần dành trước, dừng và báo trước lượt tiếp theo. Có thể tốn thêm ít nhất một request đang bay; không hứa hardcap45nghìn khi provider chưa tính usage cuối.
- Judge model chưa được phép: pilot đầu dùng review thủ công theo rubric khóa. Nếu sau đó duyệt faithfulness judge, tối đa3request được trừ từ40nghìn tokens judge đã đề xuất; không đổi tên custom judge thành RAGAS. RAGAS Faithfulness chưa có kết quả mới.
- Ghi mọi attempt/contexts/output/citations/verdict/usage/latency/fingerprint/policy/corpus SHA vào thư mục mới. HTTP thật, fixture calls và số tokens phải tách biệt. Giữ mọi failure, kể cả S06 cũ; không chạy lại S06.
- Chấm Answerable Coverage = số ca answerable có câu trả lời hợp lệ /3; False Abstention Rate = ca answerable bị từ chối /3. Từ chối C01/C02/C03 không là câu trả lời đúng. Citation Accuracy phải xét hỗ trợ ngữ nghĩa, đúng phiên bản/điều/khoản; kiểm integrity hay fake judge không đủ. Faithfulness/correctness chưa đo thì ghi null, không ước lượng điểm.

## Quan hệ với evaluation đã khóa

Bộ20+4+8 và gold answers không đổi. Pilot benchmark Phase2B vẫn là S01,S04,X01,N02,N07,N08, không thay bằng C01–C03. Ba ca mới là acceptance hiện hành phục vụ mục tiêu Phase2C; kết quả không nhập/chọn lọc để làm đẹp chỉ số benchmark32ca. Toàn chi phí dùng chung phần ngân sách đã nêu, không lập một ngân sách benchmark riêng rồi chọn báo cáo đẹp.

Sau khi có cấu hình cuối được duyệt, benchmark khóa chạy trên cùng cohort và giữ đầy đủ adverse attempts. Vì retrieval/policy/corpus đã đổi, không dùng Recall@5 hoặc model scores của Phase2B làm kết quả cho candidate này. Diagnostic retrieval offline của pilot khóa (nếu được chạy) phải báo rõ số ca cógold, backendSQLite và không suy tương đươngPostgreSQL.

## Giới hạn cần thể hiện trong UI và báo cáo đồ án

- Chỉ Vành đai4 tại Hà Nội; giải thích quy định theo mốc ngày đã được review, không bao phủ mọi chính sách2026 hoặc mọi hồ sơ chuyển tiếp.
- Phân biệt ngày snapshot gốc với ngày review theo phạm vi; không đổi ngày kiểm toàn corpus thành ngày review vài điều.
- Không xác định thửa đất, tính tiền, bảo đảm quyền lợi/suất/vị trí tái định cư hoặc cơ quan nhận hồ sơ chưa duyệt.
- Cần loại đất, giấy tờ đã ẩn danh, mốc quyết định/phương án, nhu cầu di chuyển và nhà/đất khác khi kết luận hồ sơ. Không yêu cầu CCCD, số thửa hoặc địa chỉ nhà.
- NQ36 và các nhánh nhà nhà nước/tài sản không hợp pháp/tái định cư khác, cơ chế258/90, hệ số/đơn giá chưa mở không được suy từ quy định chung.
- Scope mới chỉ cho ngày21/10. Demo ngày23/10 phải chọn rõ mốc21/10 hoặc review thật cho mốc mới; không tự kéo dài receipt/checked_at.

Vòng này chỉ chuẩn bị nội dung cần hiển thị; chưa thay giao diện ngoài phạm vi sửa coverage.
