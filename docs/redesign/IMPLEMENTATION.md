# Triển khai phiên bản cho người dân

Trạng thái này mô tả mã nguồn trong workspace. Triển khai lên dịch vụ công khai, phát hành corpus và chứng nhận chất lượng là các bước riêng, chỉ được ghi hoàn tất khi có bằng chứng tương ứng. [Báo cáo triển khai](../../reports/citizen-implementation-20261019/README.md) lưu kết quả kiểm tra và giới hạn của đợt này.

## Chức năng đã có trong mã nguồn

Trang đầu dùng sáu tình huống đời thường. Người dùng chọn để điền câu hỏi, sửa rồi chủ động gửi. Luồng nhận giấy chưa biết tên chỉ hỏi tên giấy; có lựa chọn không rõ và không yêu cầu ảnh, số thửa hoặc định danh. Dữ kiện người dùng sửa ở lượt hiện tại được ưu tiên hơn lịch sử; lời assistant không trở thành dữ kiện về hồ sơ.

Câu hỏi chung có chữ “tôi” vẫn có thể được giải thích mà không đòi hồ sơ riêng. Yêu cầu xác nhận quyền lợi cá nhân tiếp tục bị giới hạn. Khi model thiếu thông tin, runtime chọn một câu hỏi cố định về ngày, địa bàn, loại đất hoặc giai đoạn; không hiển thị tự do câu hỏi thu thập hồ sơ của model. Lựa chọn không biết giúp thoát vòng hỏi lại.

Đáp án có `answer_schema_version=2`. `answer_sections` chỉ tham chiếu nguyên văn claim đã verify; nguồn mở tại đúng claim. Nội dung sao chép dùng cùng projection. `answer_notices` giữ các thông báo giới hạn cố định của runtime, gồm khoảng trống nguồn lịch sử; không lấy từ summary của model. Dữ liệu v2 sai cấu trúc bị chặn hiển thị, sao chép và mở nguồn. Câu trả lời cũ tiếp tục đọc bằng `content`.

Mọi hướng dẫn thực chất phải nằm trong claim trước verify. `Draft.next_steps` không còn được phát ra client. Cổng veto cả nhóm, ngân sách mỗi lượt, graph, model và embedding contract giữ nguyên. Không có bước paraphrase hoặc sửa điều kiện sau verify.

## Nguồn thủ tục và liên hệ

Schema, ingest và catalogue nhận `official_procedure`/`official_directory`, metadata tác vụ, địa bàn, mã thủ tục và phụ thuộc. Danh bạ chỉ chứng minh thông tin liên hệ công khai; không chứng minh thẩm quyền nhận/giải quyết hoặc quyền lợi. Tin dự án không chứng minh checklist hay thủ tục.

Claim về tác nghiệp cần tất cả nguồn được rà soát `unchanged` trong bảy ngày, kể cả khi cho phép giải thích snapshot cũ. Receipt phải khớp checksum, có bằng chứng nguồn và xác nhận đã kiểm tra vai trò, thẩm quyền/địa bàn, thủ tục cùng phụ thuộc. Receipt mới nhất ghi changed/unavailable hoặc thiếu xác nhận làm nguồn không đủ điều kiện. Claim còn được kiểm tra lại tuổi receipt tại finish. Đây là kiểm tra cấu trúc; verifier và reviewer vẫn phải đọc nội dung, đối tượng và điều kiện cụ thể.

Directory chỉ được giữ số liên hệ trong chunk sau rà soát tường minh rằng đó là liên hệ cơ quan công khai và không chứa dữ liệu cá nhân. Các nguồn khác tiếp tục qua redaction hiện có. Không bỏ lọc dữ liệu cá nhân cho toàn corpus.

[Ma trận yêu cầu nguồn](../../data/citizen_source_requirements.json) và [danh sách tìm nguồn](../../data/source_candidates/citizen-v2.json) là worklist, không phải nguồn đã duyệt. Lệnh sau chỉ kiểm kê candidate, không gọi model, embedding hoặc ghi database:

```bash
.venv/bin/python scripts/audit_citizen_coverage.py \
  --snapshot <candidate.json> \
  --output <report-directory>/source-worklist.json
```

Không có nguồn thủ tục/danh bạ phù hợp thì runtime nói rõ chưa chỉ được nơi nộp, địa chỉ hoặc số điện thoại. Không đưa candidate chưa duyệt vào `sources.json`, active corpus hoặc câu trả lời để làm cho tính năng có vẻ đầy đủ. Không embedding lại corpus chỉ vì đổi metadata hoặc lọc phạm vi.

## Bộ đánh giá và công bố

Ba suite khóa cũ giữ nguyên. Registry bổ sung tại `data/evaluation/registry.json`; draft không chạy được như suite frozen. Suite mới muốn chạy phải có checksum/count, corpus binding, ngày, rubric, answerability, trạng thái annotation/review và, với ca answerable, proposition/evidence groups/gold đã duyệt. Generation và retrieval đều kiểm tra corpus binding và gold thuộc corpus được chọn.

Fingerprint runtime bao gồm policy/schema mới; metadata đánh giá ghi riêng fingerprint giao diện. Resume bị chặn khi giao diện đã thay đổi. Export và public projection nhận suite đăng ký đã freeze, giữ ca chưa chạy và tách cohort cũ/mới. Metrics tác vụ có mẫu số answerability cố định; từ chối trên ca answerable không thể được tính pass. Evidence groups hỗ trợ nhiều alternative đã duyệt; phải đủ mọi chunk trong một alternative cho từng group. Retrieval và citation coverage công bố riêng, không biến việc có đủ nguồn thành kết luận diễn giải đúng. Chưa triển khai chấm tự động mức hiểu của người dùng, thẩm định pháp lý độc lập hoặc chứng nhận journey từ draft.

Trang đánh giá giữ lịch sử trong mục mở rộng và nói rõ điểm cũ không chứng nhận phiên bản mới. Không sửa báo cáo hoặc verdict lịch sử cho khớp code mới. Cổng phát hành kỹ thuật hiện hành vẫn giữ tiêu chí cũ; không được diễn giải việc vượt cổng đó là đạt các mục tiêu v2 về người dân, journey hoặc pháp lý.

## Handoff giao diện

Các frame bổ sung nằm cùng trang UI UX Redesign, giữ font, tokens và component đã thống nhất. Frame gốc vẫn được giữ để đối chiếu:

| Màn hình | Desktop | Mobile |
|---|---|---|
| Trang đầu sáng | [25:404](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-404) | [25:453](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-453) |
| Làm rõ tên giấy sáng | [25:483](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-483) | [25:536](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-536) |
| Trang đầu tối | [25:572](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-572) | [25:621](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-621) |
| Làm rõ tên giấy tối | [25:651](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-651) | [25:702](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=25-702) |

Implementation co giãn với nội dung thật; composer còn truy cập được trên màn hình thấp. Không dùng screenshot Figma làm giao diện hoặc URL asset tạm trong code.

## Việc còn lại trước phát hành đầy đủ

1. Reviewer nguồn/pháp lý chốt phạm vi thủ tục, phụ thuộc, địa bàn và ngày áp dụng; bổ sung raw, provenance, source review cùng corpus candidate thực. Không coi worklist là hoàn tất bước này.
2. Annotation và freeze một phiên bản bộ dev mới; giữ draft hiện có để truy nguyên. Ca bổ sung sau prompt là phiên bản đánh giá tiếp theo. Holdout độc lập và nghiên cứu người dùng phải do quy trình nêu trong EVALUATION tổ chức, không tự gán đã đạt.
3. Chạy model trên PostgreSQL riêng, review gắn checksum, kiểm tra journey và hai vòng usability theo kế hoạch. Kết quả SQLite chỉ là chẩn đoán riêng.
4. Đóng gói corpus nếu có thay đổi, restore vào database riêng, chạy readiness và live checks trên SHA đã kiểm thử, xác minh identity/capability/UI trước rollout. Giữ release cũ tới khi phát hành và restore đạt; rollback không phục hồi hội thoại server.

Không cần đổi pipeline, model, hosting hoặc phát triển tính toán bồi thường/GIS để hoàn thành các bước này.
