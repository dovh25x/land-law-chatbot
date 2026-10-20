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

## Candidate chất lượng kế tiếp

[Patch riêng](next-quality-candidate.patch) và [biên bản](next-quality-candidate.json) chuẩn bị cách giữ quan hệ nhân quả của thiệt hại, đồng thời tập trung câu hỏi về điều kiện trước một bước vào toàn bộ điều chi phối và các dẫn chiếu cần thiết; vẫn giữ bằng chứng từ văn bản khác. Hồi quy mới tái hiện2 lỗi trước sửa; toàn bộ309 test backend trong worktree riêng đạt sau sửa. Chưa gọi Groq, chưa merge và chưa deploy patch này; không coi đây là bằng chứng model đã cải thiện. SHA phát hành giữ nguyên logic đã được đo ở cohort `release-policy-evaluation`.

## Cấu hình kết hợp sau gián đoạn

Retry S04 ở cấu hình `e409d8ac` đã trả lời nhưng dùng sai mốc pháp luật; [review-v3](release-policy-evaluation/review-v3/smoke/results.md) giữ kết quả là fail và vẫn giữ attempt TPD trước đó. Bản veto riêng `aab57560` chỉ đo16 ca guard/source-fact, không có điểm nội dung LLM. Sau đó đã tích hợp patch N01/N04 cùng veto S04 vào SHA `bddeded`; toàn bộ311 test backend đạt. [Cohort mới](final-quality-evaluation/) bắt đầu lại theo fingerprint riêng, giữ nguyên bộ32 và không nhập pass của các bản cũ. Trạng thái nghiệm thu vẫn chờ bằng chứng mới, không chuyển điểm unit test thành model pass.

## Checkpoint cuối của cấu hình kết hợp

[Biên bản hiện tại](evaluation-checkpoint-status-final.json) có21/32 ca đã thực thi:19 pass,2 fail,11 chưa chạy. Trong19 pass có16 ca guard/source-fact không gọi LLM và3 ca nội dung N01/N04/S04 đã đối chiếu nguồn; không gọi19/32 là độ chính xác pháp luật. S06 abstention an toàn do model vẫn gán sai khoản; X02 bị lỗi định dạng rồi TPD200.000 (used196.765, requested4.134). [Review gắn checksum](final-quality-evaluation/review-v1/natural/results.md) và các suite kề bên giữ mẫu số đầy đủ. CI của SHA `bddeded` đạt311 backend, frontend unit/build/E2E và giới hạn Docker512MiB. Không có tiến trình benchmark tự tiếp tục tranh quota với public sau checkpoint này.

## Deployment đã xác minh

Đã triển khai SHA `d2424ed5469df05d0994b56daa02d4765323ae83` lên [địa chỉ phục vụ](https://hanoi-land-law.pages.dev). SHA này chỉ thêm báo cáo sau runtime `bddeded` và bản thân nó cũng đạt [CI đầy đủ](https://github.com/dovh25x/land-law-chatbot/actions/runs/39412230786):311 backend,14 frontend unit,100 E2E, build, secret scan, audit và Docker383,004MiB/512MiB. [Bằng chứng phần mềm đúng SHA](software-d2424ed.json) giữ nguồn đo; không chuyển kết quả test thành chứng nhận pháp luật.

[Identity live](production-identity.json) xác nhận cả Render Free và Pages cùng SHA, fingerprint `83f93f6482ed90765a62c39c818d5972e3560e2a2357efa21cd55f13be603b9e`, PostgreSQL và corpus `corpus-a26bc99e541fbbe2` với60 tài liệu/7.392 chunks, vector384 chiều. Runtime không có quyền SELECT/INSERT trên messages/traces/answer_cache; signed ingress chặn truy cập API trực tiếp. [Giao diện thực](live-navigation/navigation.json) đạt điều hướng/thư viện/nguồn/biểu thị đánh giá cũ trên1440,390 và320px, không giả API. Đây là mô phỏng mobile bằng Chromium, chưa kiểm tra thiết bị vật lý.

[Public controls](public-controls.json) đạt các nhánh thiếu challenge400, token phiên sai404 và history đã ngừng410. [Turnstile thật](live-turnstile.json) không cấp token cho trình duyệt headless trong thời gian kiểm tra; không vượt challenge. Vì vậy chưa xác minh chat public, chu trình IndexedDB reload/xóa hoặc LLM trên đường public. Các lần gọi model trong benchmark không thay thế kiểm tra này. [Deployment cũ](rollback-retained.json) vẫn còn; không thực hiện rollback đè serving.

[Trạng thái phát hành](release-status.json) tách rõ **deployment kỹ thuật đã xong** và **nghiệm thu chất lượng đầy đủ chưa đạt**. Giữ nguyên profile `academic_prototype`, cảnh báo nguồn cũ và các cổng chất lượng đang fail; không thay ngưỡng, không kích hoạt corpus candidate và không tuyên bố hoàn tất sản phẩm v2. Miễn trừ reviewer/nghiên cứu người dùng không bao gồm S06, quota Groq, các ca chưa chạy, coverage hoặc freshness. Không có tiến trình nền tự chạy tiếp.
