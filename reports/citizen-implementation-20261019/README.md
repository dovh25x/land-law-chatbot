# Triển khai giao diện và luồng hỏi đáp cho người dân

Báo cáo của workspace ngày 19/10/2026. [Trạng thái chức năng](../../docs/redesign/IMPLEMENTATION.md) mô tả phần đã triển khai và phần cần nguồn/reviewer/nghiên cứu người dùng. Đây chưa phải receipt phát hành hoặc chứng nhận pháp lý.

## Thay đổi

- Sáu điểm vào theo tình huống; một câu làm rõ có lựa chọn chưa biết; chọn để điền, sửa rồi gửi; giữ lịch sử cũ.
- Schema đáp án v2, phần trả lời tham chiếu claim đã verify, mở đúng citation, sao chép cùng projection; chặn projection lỗi. Thông báo giới hạn cố định không bị mất khi render cấu trúc.
- Prompt ưu tiên tiếng Việt dễ hiểu và giải thích thuật ngữ trong claim. Hành động phải vào verify; bỏ đường hiển thị `Draft.next_steps` chưa được kiểm chứng. Giữ veto cả nhóm.
- Policy procedure/directory, receipt tác nghiệp bảy ngày, kiểm tra dependency/source role, chặn directory suy ra thẩm quyền; metadata và ingest có cổng rà soát liên hệ công khai.
- Registry bộ đánh giá mới, chặn draft, bind corpus/gold, evidence groups có alternatives, mẫu số tác vụ cố định và false abstention. Giữ nguyên byte ba suite khóa, báo cáo lịch sử và active corpus.
- Handoff Figma bổ sung tám frame trên cùng hệ thiết kế; không thay hướng thiết kế hoặc đưa ảnh chụp vào giao diện.

## Bằng chứng

[check-attempts.json](check-attempts.json) giữ log trước/sau, kể cả các lần thất bại. [source-identity.json](source-identity.json) ghi base SHA và checksum từng file của workspace; base SHA một mình không đại diện các thay đổi chưa commit. [identity.json](identity.json) ghi fingerprint và checksum suite/manifest.

Các lần E2E trước đã tìm thấy bốn lỗi gồm note locator trùng và composer mất khỏi vùng nhìn trên màn hình thấp; đã sửa và có lần full suite đạt 94/94. Khi thêm test metrics mới, một test gộp ba viewport vượt deadline tổng trong lần full 96 ca; log/trace được giữ ở [e2e-timeout-attempt](e2e-timeout-attempt). Test được tách thành context riêng cho mỗi viewport, giữ nguyên assertion và deadline, không tăng timeout để che lỗi. Kết quả cuối được ghi trong software-checks.json khi hoàn tất.

[Source worklist](source-worklist.json) chỉ kiểm kê candidate, không xác nhận đủ nguồn pháp lý. [Ma trận yêu cầu](../../data/citizen_source_requirements.json) và [nguồn cần đọc](../../data/source_candidates/citizen-v2.json) chưa được đưa vào corpus phục vụ. Không tạo receipt giả, không embedding lại và không đổi active database.

## Đánh giá thật và giới hạn

Kế hoạch tám câu natural khóa nằm ở [model-evaluation-plan.json](model-evaluation-plan.json); [evaluation-authorization.json](evaluation-authorization.json) ghi chấp thuận của chủ dự án. Lệnh ban đầu bị automatic review từ chối trước khi thực thi vì egress chưa rõ; chỉ chạy lại sau khi người dùng chấp thuận đích Groq và payload.

Đợt `model-natural-attempt-1` dùng database PostgreSQL mới, được giữ lại theo receipt; không migrate/restore đè database đang phục vụ. Fingerprint runtime của PostgreSQL khác SQLite. Mọi output model chưa verify và attempt được giữ theo checksum để chẩn đoán, chỉ gồm benchmark giả lập và corpus chính thức. Không dùng các output này như câu trả lời pháp lý được duyệt.

`offline-guards-attempt-1` bị treo trong sandbox trước khi ra kết quả và đã dừng; không gọi model. Lần ngoại tuyến thứ hai cưỡng chế `--no-generation`, chạy riêng N07/N08 và giữ mẫu số natural 8. Hai trạng thái là clarification_needed/insufficient_evidence, tổng LLM request bằng 0. Kết quả này không được trộn vào cohort PostgreSQL gọi model thật.

Các phép đo phần mềm không xác nhận model giữ đủ điều kiện pháp lý hoặc người dân hiểu đúng. Bộ v2 vẫn là draft; chưa có gold pháp lý đã duyệt, holdout độc lập, journey thật hoặc thử nghiệm người dùng. Nguồn procedure/directory chưa được duyệt nên chưa phát hành hướng dẫn nơi nộp/checklist cụ thể. Chưa deploy, phát hành corpus mới hoặc chạy live checks trên production.

## Kết quả bàn giao cuối

[Software checks](software-checks.json): **275 backend, 14 frontend unit, 100 E2E đều đạt**; build và secret scan đạt. Python/Node thực tế được ghi trong receipt; đây không phải live test của image production. [Ảnh desktop](ui/citizen-clarification-desktop.png) và [mobile](ui/citizen-clarification-mobile.png) là screenshot browser với fixture, đã được kiểm tra trực quan, không phải đáp án pháp lý thật.

[Source identity cuối](source-identity-final.json) và [fingerprint cuối](identity-final.json) thay cho identity ban đầu khi đánh giá trạng thái hiện tại. File identity ban đầu được giữ để truy nguyên đợt model chạy trước bản sửa N02.

[Đánh giá Groq/PostgreSQL](model-reviewed-attempt-1/results.md) mới hoàn tất **3/8 ca**, còn **5 chưa chạy** vì TPD. Review kỹ thuật: N01 fail do không hoàn tất (draft bị verifier bắt lỗi căn cứ, repair gặp TPM); N02 fail vì thiếu điều kiện và đơn vị trong diễn giải dù citation khớp; N03 fail do TPD. Không lấy hỏi lại hoặc lỗi quota để cộng điểm trả lời.

N02 được giữ nguyên verdict fail và output gốc. Fixture thực tế tại `tests/fixtures/citizen-n02-qualification.json` tái hiện việc verifier đồng ý vẫn để lọt diễn giải thiếu điều kiện. Log [trước sửa](logs/citizen-n02-regression-before.log) có 1 fail/1 pass. Patch thêm veto điều kiện đủ điều kiện bồi thường và đơn vị cho một nhân khẩu trước phát đáp án, giữ toàn nhóm fail; không nối thêm điều kiện sau verify. Toàn bộ 275 backend tests đạt sau patch. Fingerprint runtime đã đổi, nên kết quả model trước patch không chứng nhận code cuối. [Model status](model-status.json) ghi rõ giới hạn này.

**Chưa đủ điều kiện phát hành.** Không deploy hoặc đổi corpus phục vụ. Trước đợt tiếp theo cần đủ capacity Groq rồi chạy natural trên cấu hình cuối trong output mới (không resume fingerprint cũ), review đủ mẫu số, bổ sung/rà soát nguồn thủ tục và directory, annotation/freeze v2, kiểm tra các hành trình và nghiên cứu người dùng. Nguồn mới vẫn phải đóng gói/restore DB riêng; không lấy software checks hoặc regression N02 làm thẩm định pháp lý.
