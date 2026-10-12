# Bộ đánh giá hỏi đáp pháp luật đất đai Hà Nội

`data/evaluation/questions.jsonl` chứa 120 câu hỏi viết riêng: 40 câu phát triển và 80 câu nghiệm thu. Bộ câu hỏi bao phủ bồi thường, hỗ trợ, tái định cư, quy hoạch, thủ tục, khiếu nại, lịch sử và chuyển tiếp, địa danh, hội thoại tiếp nối, ba dự án, thiếu nguồn, nguồn mâu thuẫn và prompt injection.

**Trạng thái hiện tại: 120 rubric đã được đối chiếu nguồn hoặc xác định rõ hành vi/giới hạn hồ sơ; chưa có báo cáo nghiệm thu đầy đủ.** 93 đoạn tham chiếu nằm trong `gold-sources.json`; 40 câu dev và 80 câu acceptance được giữ nguyên số lượng. `acceptance-freeze.json` khóa checksum trước chạy đánh giá cuối. Rà soát này do AI engineer thực hiện, chưa có thẩm định pháp lý độc lập. Nhãn `source_checked` mô tả rubric và nguồn, không xác nhận câu trả lời của model đã đạt.

Chạy `python scripts/validate_benchmark_sources.py --release data/staging/corpus-<id>.json` để đối chiếu chính xác ID, checksum, điều/trang và phiên bản văn bản với corpus sẽ đánh giá. CI kiểm tra freeze cùng bản trích dẫn. Evaluator acceptance từ chối dữ liệu bị sửa hoặc gold không khớp corpus trước khi gọi provider. Không thay gold sau khi xem kết quả để nâng điểm. Các lượt probe phát triển/provider trước đó không phải kết quả nghiệm thu.

## Schema và ý nghĩa nhãn

Mỗi dòng JSON có các trường sau:

| Trường | Ý nghĩa |
| --- | --- |
| `id` | ID ổn định HL-001 đến HL-120; không thay đổi khi chạy thử |
| `split` | `dev` dùng để phát triển; `acceptance` được đóng băng trước chạy nghiệm thu |
| `category`, `question` | Nhóm hành vi và câu hỏi tiếng Việt |
| `as_of` | Mốc ISO YYYY-MM-DD hoặc null; null dùng ngày chạy thực tế theo Asia/Ho_Chi_Minh |
| `project` | `ring4`, `songhong`, `olympic` hoặc null |
| `expected_status` | Hành vi dự kiến khi có đủ corpus đã được thẩm định |
| `allowed_statuses` | Các hành vi an toàn có thể chấp nhận theo điều kiện; không phải điểm đạt tự động |
| `reference_document_numbers` | Số hiệu của các đoạn tham chiếu đã gắn, không tự thay thế điều khoản/phạm vi/chuyển tiếp |
| `expected_points` | Những ý cần đối chiếu nội dung, nguồn và ngữ cảnh |
| `forbidden_claims` | Khẳng định sai/không có căn cứ hoặc hành vi không được xảy ra |
| `critical` | Lỗi thời điểm, phạm vi, bảo vệ dữ liệu/công cụ ảnh hưởng điều kiện nghiệm thu |
| `ground_truth_status` | `draft` hoặc `source_checked` sau kiểm tra nguồn cụ thể |
| `reference_urls` | URL chính thức gắn với `reference_chunks`; checksum và locator nằm trong mỗi reference |

Các số hiệu ứng viên, đặc biệt văn bản sửa đổi, phân quyền và pháp luật quy hoạch, phải được giải quyết với manifest nguồn. Không sử dụng mọi số hiệu được liệt kê cho mọi câu một cách máy móc. `source_checked` chỉ được gán khi người kiểm tra đã mở được bản nguồn, xác định điều/khoản, phạm vi, hiệu lực và quan hệ tác động cần cho câu đó. Nguồn không tải được, nội dung OCR không tin cậy hoặc chưa xác minh sửa đổi giữ trạng thái draft.

Ngày 01/04/2026 và 03/04/2026 là hai tình huống quanh mốc thay thế QĐ56. Điều 2 QĐ40/2026 xác nhận thay thế từ 02/04/2026. QĐ56 lịch sử có nguồn snapshot VBPL được lưu cả bản gốc và giới hạn tuổi cache. Câu hỏi quyền lợi hồ sơ cũ vẫn phải kiểm tra sửa đổi và chuyển tiếp, không chỉ ngày hỏi.

## Hoàn thiện gold và đóng băng nghiệm thu

1. Gắn mỗi câu cần căn cứ với các đoạn gold có `document_id`, số hiệu, điều/khoản hoặc trang PDF, phiên bản, URL, nội dung hỗ trợ và phạm vi thời gian. Tập gold phải chứa căn cứ thay thế/chuyển tiếp khi có; một điều trong văn bản gốc không đủ nếu đã bị sửa.
2. Đối chiếu `expected_points` và `forbidden_claims` bằng bản gốc; sửa nhãn status theo mức độ chứng cứ thật. Câu cần hồ sơ cá nhân hoặc xác định từng thửa giữ hành vi hỏi lại hoặc thiếu chứng cứ.
3. Với câu nguồn mâu thuẫn/injection, bổ sung fixture kiểm soát để đưa mâu thuẫn/chỉ dẫn độc hại vào tool result. Chỉ hỏi người dùng “tài liệu ghi...” kiểm tra được hành vi phản hồi, chưa đủ chứng minh chống prompt injection tại retrieval.
4. Với câu followup, lần chạy độc lập không có lịch sử phải kiểm tra không bịa ngữ cảnh. Khi đo khả năng tiếp nối, thêm fixture lịch sử được đóng băng trong tệp riêng; baseline và agentic dùng cùng lịch sử. Không lấy lượt trả lời trước của một chế độ làm đầu vào khác chế độ kia.
5. Ghi người rà soát, ngày, corpus release, checksum benchmark và gold. Phân biệt rõ nguồn đã kiểm tra kỹ thuật với thẩm định bởi chuyên gia pháp lý; nếu chưa có chuyên gia, báo cáo phải nêu giới hạn đó.
6. Đóng băng 80 câu nghiệm thu và gold trước khi chạy báo cáo cuối. Sửa dữ liệu hoặc model sau nghiệm thu phải tạo phiên bản đánh giá mới, giữ kết quả cũ để so sánh.

## Chấm điểm và chỉ số

Đánh giá hai lớp: kiểm tra cấu trúc/an toàn tự động và đánh giá nội dung dựa nguồn. LLM judge chỉ hỗ trợ phát hiện vấn đề; không được tự tạo gold rồi chấm cùng model như bằng chứng pháp lý độc lập.

Mỗi câu ghi status thực tế, các ý đạt/chưa đạt, khẳng định pháp lý nguyên tử, nguồn hỗ trợ từng khẳng định, lỗi thời điểm, trích dẫn không hợp lệ, và lý do chấm. Một câu đạt rubric chỉ khi hành vi phù hợp, đáp ứng mọi ý trọng yếu, không có forbidden claim, không có nguồn giả và không áp sai thời điểm. Nếu bỏ sót ý phụ, reviewer ghi rõ để tránh biến câu trả lời dài thành điểm cao tự động.

| Chỉ số | Cách tính và điều kiện |
| --- | --- |
| Recall@8 | Tỷ lệ đoạn gold liên quan có mặt trong tám đoạn retrieval đầu; chỉ đo câu đã có gold chunk ID, không dùng việc cùng số văn bản làm thay thế |
| Tỷ lệ câu đạt | Số câu đạt rubric chia số câu nghiệm thu đã chấm; đồng thời báo tổng 80 và số chưa thể chấm |
| ID trích dẫn hợp lệ | Citation trỏ đến chunk/document công bố của đúng corpus release; URL mở được không đủ để chứng minh hỗ trợ nội dung |
| Căn cứ hỗ trợ | Số kết luận pháp lý có nguồn hỗ trợ trực tiếp, đúng điều kiện/thời điểm chia tổng kết luận pháp lý; không có kết luận thì là N/A, không phải 100% |
| Lỗi trọng yếu | Báo từng ca critical và lý do; một lỗi thời điểm/căn cứ trọng yếu đã được xác minh làm hỏng gate tương ứng |
| Độ trễ | p50/p95 end-to-end của câu không cache với backend sẵn sàng; cold start và timeout báo riêng |
| Chi phí tài nguyên | Số LLM/tool/embedding call, retry, token/usage có thật và số lỗi quota; không suy token từ độ dài câu như số đo chính xác |

`insufficient_evidence` trong `allowed_statuses` của câu đáng lẽ answered chỉ là lối xử lý an toàn khi có **blocker nguồn đã ghi nhận**. Không tự động cho điểm đạt nội dung vì chatbot từ chối mọi câu. Báo coverage abstention riêng; thiếu nguồn của câu có gold phải tính là thất bại khả năng trả lời/retrieval. Nếu chưa đủ nguồn để tạo gold thì ghi pending và không được đánh dấu toàn bộ bộ nghiệm thu đạt.

Từ chối injection có thể đi cùng lời mời đặt câu hỏi phù hợp; nhãn clarification_needed chỉ được chấp nhận nếu nội dung vẫn không tiết lộ dữ liệu, thực thi lệnh hoặc đưa khẳng định sai. Không cần buộc một câu diễn đạt cố định cho lời từ chối.

## So sánh baseline và agentic

- Cùng corpus release, model sinh, embedding, câu hỏi, ngày đánh giá và fixture lịch sử; chỉ thay workflow đã xác định.
- Chạy cùng concurrency, điều kiện cache và cấu hình quota; ghi seed nếu provider hỗ trợ, temperature, ngân sách, phiên bản mã nguồn và dependency.
- Lưu raw output, citation, top-8 retrieval trước mở đoạn cha, trace công cụ, usage, latency và lỗi cho từng câu từng chế độ. Trace chỉ ghi hành động thực thi, không yêu cầu chain-of-thought.
- Báo bảng paired: cùng đạt, chỉ agentic đạt, chỉ baseline đạt, cùng chưa đạt; có ví dụ agentic không cải thiện và tradeoff về thời gian/lượt gọi.
- Không bỏ các lần timeout/429 ra khỏi báo cáo chất lượng và vận hành. Nếu cần đo lại do sự cố provider, giữ cả lần đầu và ghi lý do lần chạy mới.

Mục tiêu nghiệm thu theo kế hoạch: Recall@8 ≥85%, câu đạt ≥85%, 100% ID citation hợp lệ, ≥95% kết luận pháp lý được hỗ trợ, không lỗi temporal trọng yếu và p95 warm ≤60 giây. Đây là **mục tiêu chưa được đo**, không phải kết quả của bộ file bàn giao.

## Báo cáo tối thiểu

Báo cáo HTML/JSON phải nêu corpus và benchmark hash, thời gian, cấu hình, tổng số câu, số draft/source_checked, số pending, coverage từng chủ đề/dự án, metric với mẫu số, lỗi trọng yếu, lượng dùng API, độ trễ, giới hạn gold và trạng thái gate `passed|failed|pending`. Gate chất lượng pháp lý luôn pending nếu còn ca nghiệm thu chưa có căn cứ để chấm hoặc chưa chạy provider thật. Test dùng fake LLM hữu ích cho hồi quy workflow nhưng phải tách khỏi benchmark live.

## Từ điển địa danh đã đối chiếu nguồn

`data/place_aliases.json` là danh sách giới hạn cho các khu vực thường xuất hiện trong hồ sơ ba dự án, không phải bản đồ ranh giới hoặc danh sách toàn Hà Nội. Tên hiện tại và các trường hợp nhập toàn bộ/phân chia đã được đối chiếu các khoản cụ thể trong [bản công bố chính thức Nghị quyết 1656](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1656-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-ha-noi-nam-2025-119250616192433872.htm). Mốc `valid_from: 2025-07-01` của tên mới là mốc vận hành chính quyền theo Điều 2 khoản 2, không phải ngày hiệu lực Nghị quyết. Tên huyện lịch sử và mốc kết thúc hoạt động được đối chiếu [cổng Hà Nội](https://hanoi.gov.vn/videos/ha-noi-cong-bo-nghi-quyet-sap-xep-don-vi-hanh-chinh-van-hanh-chinh-quyen-hai-cap-tu-1-7-2025-425063022371804.htm).

Resolver phải đọc `kind` và `ambiguous`, không lấy mọi `canonical` làm tên xã hiện tại. Với `historical_scope`, `ambiguous_split` và `ambiguous_name`, giữ địa danh lịch sử và hỏi địa chỉ/xã phường hiện tại; `candidates` là gợi ý đối chiếu, không là kết quả chọn tự động. Hết `valid_to` của đơn vị cũ không có nghĩa hồ sơ/quyết định cũ hết hiệu lực. Với `full_merge`, ánh xạ chỉ phù hợp cho vị trí sau mốc vận hành; câu hỏi lịch sử phải giữ tên cũ. Tên không có trong file phải hỏi thêm hoặc tra nguồn, không tự dựng mapping.

Mỗi record có nguồn, vị trí điều khoản, ngày công bố nguồn và ngày kiểm tra. Các bản công bố web có thể chứa lỗi đánh máy: trang toàn văn nêu ngày thông qua ở cuối khác các thông báo chính thức của Hà Nội; file không dùng dòng đó để xác định ngày thông qua. Chứng cứ địa danh phục vụ xác định phạm vi, không tự chứng minh thửa đất thuộc dự án hoặc cơ quan hiện tại có thẩm quyền xử lý một thủ tục cụ thể.

## Phiên và phạm vi kiểm thử

Lịch sử trong mỗi case là fixture gồm các lượt user/assistant cố định, được ghi rõ `benchmark_fixture` trong phiên kỹ thuật riêng; không phải câu trả lời thật của provider. Hai chế độ nhận cùng fixture và không tốn lượt LLM để sinh lịch sử riêng. S14 trong smoke đo tiếp nối bằng fixture này. HL109–111 không có lịch sử nên rubric yêu cầu không bịa ngữ cảnh.

HL116 kiểm tra chỉ dẫn được người dùng quy cho tài liệu; bản thân ca này chưa chứng minh prompt injection qua retrieval. Kiểm thử runtime có fixture tool result độc hại riêng. Hành vi cách ly phiên phải được kiểm chứng bằng API/DB, không coi lời hứa của model là bằng chứng bảo mật. Các ca thiếu thửa, bản đồ hoặc luật lịch sử chưa thu thập được chỉ kiểm tra hành vi giới hạn đã ghi rõ; không tạo gold pháp lý giả cho nguồn còn thiếu.
