# Hoàn thiện phát hành sau thay khóa Groq

Đợt này tiếp tục triển khai theo thiết kế cho người dân, giữ GPT-OSS 120B, E5 ONNX Q8 384 chiều và hạ tầng Free. Khóa mới được cập nhật qua kênh secret của Render và GitHub; không lưu giá trị khóa trong báo cáo. Quota public của ứng dụng không bị tắt; operator và public vẫn chịu quota thật của Groq.

## Phần mềm và lỗi đã sửa

Schema sinh claim chỉ cho phép loại/section phù hợp nguồn đã duyệt. Kiểm chứng và veto cả nhóm vẫn chạy sau sinh. Bổ sung regression từ output Groq thực cho nhầm nhóm đối tượng thành giấy tờ, mất nguồn gốc đất hoặc điều kiện bồi thường bằng tiền, và thay hoàn thành bố trí tái định cư bằng phê duyệt phương án. Không tự nối điều kiện vào đáp án sau verify.

Prompt gọn hơn, đoạn quy định trực tiếp về thứ tự được ưu tiên trong nhóm bằng chứng. Synthesis/verification dùng reasoning `medium`, planner vẫn `low`; cùng model, cap 2.048 token/request và ngân sách 6 request, 12 tools, hai retrieval, một repair, 90 giây. Chỉ lưu JSON kết quả benchmark giả lập, không reasoning hoặc hội thoại thật.

Harness khôi phục hooks sau từng suite và giữ thời gian chờ token bucket theo header thật qua ranh giới suite/process. Không reset counters/cooldown. [Software](software-5a428bc.json) và [CI](ci-5a428bc.json) ghi SHA đã kiểm thử; số liệu thuộc phiên bản báo cáo, không phải chứng nhận pháp lý.

## Đánh giá

Giữ nguyên byte smoke20, supplemental4 và natural8. Mọi cấu hình có output/fingerprint riêng. Không chuyển pass giữa các fingerprint hoặc sửa artifact cũ.

- [Cấu hình đang phục vụ trước đợt sửa, chạy tiếp đủ32](evaluation-resumed/review-v1/natural/results.md): smoke19/20, supplemental1/4, natural4/8 theo rà soát kỹ thuật. S06 và X02 có lỗi nội dung được phát hành; kết quả đã được giữ là fail.
- [Thử giới hạn schema](schema-policy-evaluation/review-v1/natural/results.md) và [thử prompt/thứ tự](operative-policy-evaluation/review-v1/natural/results.md): dừng sau khi phát hiện lỗi thực, giữ cả output sai và biên bản dừng; không dùng các pass ở đây để đại diện cấu hình sau.
- [Cấu hình mới nhất](release-policy-evaluation/): natural đã thực thi đủ8, không limited/error. Rà soát có6 pass,1 partial,1 fail. Trong **sáu câu cần nội dung pháp luật:4 pass,1 partial,1 fail**; hai pass còn lại là guard. N01 chưa nói rõ quan hệ thiệt hại với quá trình tháo/vận chuyển/lắp đặt; N04 abstention an toàn nhưng chưa đạt tác vụ có nguồn. Không công bố các ca này là đạt đầy đủ.

Sau natural, Groq từ chối S04 vì TPD200.000: used196.956, requested4.675, Retry-After tối thiểu705giây. Đó là thời gian cho request bị chặn, không bảo đảm còn đủ token cho cả lượt. Checkpoint, attempt limited và mẫu số32 được giữ. Các ca guard/source-fact bổ sung chạy với chốt cấm gọi provider; không dùng chúng làm độ chính xác nội dung LLM. Không chạy lại đáp án đã hoàn tất để chọn kết quả đẹp.

[Checkpoint tổng hợp](evaluation-checkpoint-status.json) giữ23/32 ca đã thực thi và9 ca chưa chạy:20 pass,1 partial,2 fail, trong đó một fail là attempt TPD. [Readiness tính lại](readiness-v1.json) vẫn `ready=false` ở coverage, freshness và ba suite generation. Không tắt cổng hoặc sửa ngưỡng để công bố đạt.

Rà soát là AI đối chiếu rubric và snapshot, không phải reviewer pháp lý độc lập. [Miễn trừ đã được chủ dự án cho phép](../production-readiness-20261020/acceptance-waiver.json) chỉ áp dụng reviewer độc lập và nghiên cứu người dùng trước phát hành; không đổi ngưỡng hoặc biến phần chưa đo thành pass.

## Corpus và nguồn

[Đối chiếu kỹ thuật60 nguồn](active-source-refetch.json) có58 nguồn tái lập nguyên vẹn chunks. QĐ56/2024 trả403; NQ254/2025 trả trang không được parser nhận là toàn văn. [Chẩn đoán](active-source-followup.json) giữ kết quả thực. Không tạo receipt freshness từ hash tải lại hoặc tự chứng nhận không có sửa đổi.

[Nguồn danh bạ](city-directory-source-review.json) đã được đọc trọn PDF một trang, đối chiếu trang công bố và cổng Hà Nội. Chỉ chứng minh địa điểm công khai của Trụ sở Tiếp công dân Thành phố, không chứng minh nơi nhận/giải quyết một hồ sơ, giờ làm việc hoặc điện thoại. Attachment để trống số/ngày nên không khẳng định số văn bản trên PDF.

[Candidate cộng thêm nguồn này](city-directory-candidate.json) giữ nguyên60 tài liệu/7.392 vector cũ và chỉ thêm một vector E5 cục bộ. [Restore/retrieval SQLite](directory-candidate-restore/sqlite/restore-and-retrieval.json) và [PostgreSQL](directory-candidate-restore/postgresql/restore-and-retrieval.json) đều đã đo riêng. [Kiểm tra runtime role và policy](city-directory-runtime-policy.json) cho phép địa chỉ thuần sau receipt, chặn suy nơi nộp/thẩm quyền và chặn dùng danh bạ hiện tại cho ngày quá khứ. Không gọi Groq trong các kiểm tra candidate. Đây là staging, chưa được phép kích hoạt; vẫn cần receipt tác nghiệp và đánh giá gắn corpus candidate. Lần đóng gói đầu gặp field embedding bị loại khỏi serializer; giữ log thất bại, sau sửa đóng gói thành công. Không có embedding cũ được tạo lại.

Bản native QĐ10/2017 cũng đã tải được từ nguồn chính thức, có checksum trong [attachment receipt](source-attachments-1.json), nhưng chưa được duyệt toàn văn để kích hoạt. Các khoảng trống lịch sử khác và bộ48 tình huống/8 journey v2 chưa freeze vẫn còn. Không xóa chúng để làm readiness đạt.

## Phạm vi phát hành

Giữ [profile hiện hành](../production-readiness-20261020/RELEASE_PROFILE.md): `academic`/`academic_prototype`; `REQUIRE_QUALITY_READINESS=false` vốn có không bị thay đổi. Phát hành bản vá phần mềm không đồng nghĩa nghiệm thu chất lượng đầy đủ. Tình trạng deployment, identity và live checks được ghi riêng trong `release-status.json` khi có bằng chứng.

Corpus serving vẫn là `corpus-a26bc99e541fbbe2`; candidate61 tài liệu chưa thay thế nó. Không drop database, không restore đè serving, không gỡ Release hoặc deployment rollback cũ. Không có tiến trình tự động đổi khóa, chạy benchmark nền hoặc sử dụng hosting trả phí.
