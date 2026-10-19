# Dashboard đánh giá và công bố đầy đủ số liệu — 2026-10-19

Yêu cầu: công bố cả kết quả chưa tốt, thiết kế lại trang Đánh giá hệ thống để đọc và so sánh dễ hơn. Không chạy lại benchmark để chọn số đẹp, không đổi kết quả hoặc fingerprint của artifact lịch sử.

## Nội dung công bố

Bản chiếu `reports/public-evaluations.json` gồm 63 artifact: 26 báo cáo generation được nhóm thành 13 lần chạy, 35 phép đo retrieval và 2 báo cáo faithfulness. Mỗi nguồn có SHA-256 và link GitHub ghim revision. Toàn bộ số liệu có thể tải JSON từ web. Bản chiếu chỉ chứa câu hỏi benchmark khóa, nhận xét và metadata; không chứa payload đáp án, hội thoại người dùng hoặc trace chi tiết.

API giữ contract summary cũ và bổ sung archive. Mặc định chọn bộ đầy đủ gần nhất trên corpus đang phục vụ, không chọn điểm cao nhất. Partial/probe mới hơn giữ trong dropdown/lịch sử và có ca chưa chạy trong mẫu số. Các corpus/configuration/backend không được ghép thành một điểm chung. Đính chính nhận xét N02 attempt 3 hiển thị riêng, không đổi verdict gốc.

Bộ PostgreSQL đầy đủ gần nhất (configuration 8db2d701…) có 22/32 đạt, 3 một phần, 7 chưa đạt. Bộ chính 16/20 đạt; bổ sung 2/4; tự nhiên 4/8, trong đó nội dung N01–N06 chỉ 2/6 đạt đủ, N07–N08 là hỏi lại/từ chối. Probe 380801c7… chỉ chạy 1/8, còn 7 chưa chạy; không thay mẫu số bằng một ca. Đây là mô tả benchmark lịch sử, không phải độ chính xác pháp luật hoặc chứng nhận cho deployment mới.

## Giao diện

Kế thừa typography, màu sáng/tối, card và spacing từ Figma handoff 14:109; mở rộng bố cục theo yêu cầu redesign. Các con số là dữ liệu API, không lấy số minh họa trong Figma. Thanh tỷ lệ là thành phần dữ liệu động trong UI, không có sơ đồ hệ thống mới.

- Thẻ tổng quan và thanh phân bố từng suite; không gọi tỷ lệ đạt chung là độ chính xác.
- Ba mục: chất lượng trả lời, tìm nguồn/faithfulness, lịch sử. Kết quả khác phiên bản vẫn hiển thị đầy đủ, có nhãn corpus/cấu hình.
- Tìm theo mã/câu hỏi, lọc suite/verdict, mở nhận xét và thông tin từng ca; đọc được điểm chưa đạt, lỗi, chưa rà soát và chưa chạy.
- Retrieval giữ Recall@8, Hit@8, số mẫu, backend và version; faithfulness giữ mẫu chấm, số mệnh đề và judge của đúng cấu hình cũ. Evidence Hit@8 sau agent được tách khỏi standalone retrieval.
- Thống kê vận hành theo suite, số mẫu/tổng/trung vị/p95, các attempts đã giữ và luồng sinh LLM/quy tắc; không chuyển latency CLI thành latency website.
- Nút tải toàn bộ JSON công khai. Không đưa cảnh báo snapshot trở lại chat.

## Kiểm thử

Source ứng dụng: `371e8c2461f457d36f833320eb2361bb6a10c8eb`.

Backend 259 passed; frontend unit 7 passed; frontend build và secret scan thành công; toàn bộ 86 E2E passed. CI thực trên GitHub success cho backend/frontend/Docker memory 512 MiB, bằng chứng ở checks-run.json/log. Tất cả kiểm tra phần mềm dùng fixture/metadata đã khóa; không gọi LLM thật hoặc chạy lại suite chấm nội dung.

E2E kiểm tra số 22/32 và 7 fail; ghi nhận đúng nhận xét N02; tải đủ 63 nguồn; chọn probe để thấy 7 ca chưa chạy; xem đủ 35 retrieval/2 faithfulness/13 nhóm lịch sử; 320 px và hai theme. Đã xem trực quan ảnh desktop sáng và mobile tối; ảnh local-ui giữ output của lần chạy đầy đủ.

Giữ các log attempt lỗi: lần đầu có locator trùng do nhãn xuất hiện ở nhiều vùng; assertion mới nhầm chữ hoa trong nhận xét gốc; lần tiếp theo phát hiện đoạn limitations fallback bị lặp. Sửa locator/expectation và bỏ đoạn lặp, không sửa dữ liệu/nhận xét để làm test đạt. Bộ cuối đã đạt toàn bộ.

## Production đã xác minh

- Source `371e8c2461f457d36f833320eb2361bb6a10c8eb` đã live trên Pages và Render. Render `dep-dbarulcs728c739et7qg` được receipt xác nhận live/verified đúng SHA.
- [CI 39212802493](https://github.com/dovh25x/land-law-chatbot/actions/runs/39212802493) và [deploy 39212812481](https://github.com/dovh25x/land-law-chatbot/actions/runs/39212812481) đều success. Log, receipt, ảnh và navigation/fingerprint/corpus check được giữ trong report và workflow-evidence.
- Fingerprint PostgreSQL của deployment: `9b7944df0d0df400620d75b9a35ed115492f38a9ea777e87b9ec7696193f383b`. Benchmark lịch sử không được sửa để khớp fingerprint này.
- `live-ui.json`: 1440, 390, 320 px đều đạt; API công khai trả đủ 63 source/13 run/35 retrieval/2 faithfulness; đúng 22 đạt, 3 một phần, 7 chưa đạt trong 32 ca của bộ đầy đủ gần nhất. Bộ lọc fail trả 7 ca, nhận xét N02 khớp, probe còn 7 ca chưa chạy; lịch sử và cả hai báo cáo faithfulness hiển thị.
- Đã xem trực quan ảnh suite production: ba bộ có số đạt/một phần/chưa đạt riêng và giải thích 2/6 câu nội dung tự nhiên. Không gọi LLM hoặc gửi chat public trong phép kiểm tra này.
- Giữ nguyên corpus, embeddings, database và các asset Release. Metadata/report về nguồn cũ tiếp tục tồn tại; không đưa banner snapshot trở lại màn hình chat.
