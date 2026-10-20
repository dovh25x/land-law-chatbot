# Sản phẩm đích và trải nghiệm người dân

Đây là đặc tả cần triển khai, không phải mô tả khả năng đã có. Những chân dung và câu hỏi dưới đây là giả thuyết thiết kế, chưa phải kết quả phỏng vấn người dùng.

## Lời hứa sản phẩm

“Giúp bạn hiểu việc thu hồi đất liên quan Vành đai 4 Hà Nội, đọc các thông tin cần thiết trong giấy tờ, tìm quy định và nơi hỏi phù hợp.” Tên hiển thị đề xuất vẫn giữ thương hiệu Vành đai 4; mô tả có thể là “Hướng dẫn cho người dân”. Không tự nhận là cơ quan nhà nước, người giải quyết hồ sơ hoặc luật sư đại diện.

Kết quả mong muốn của một phiên là người dùng nói lại được: mình đã biết gì, điều gì chưa xác định, nguồn nào chứng minh, và việc tiếp theo cần làm hoặc hỏi. Một đáp án đúng điều luật nhưng người đọc không biết làm gì tiếp chưa hoàn thành tác vụ.

## Nhóm người dùng và công việc cần giúp

| Tình huống | Nhu cầu | Kết quả hữu ích |
|---|---|---|
| Chưa hiểu quy trình | “Nghe nói nhà ở gần đường sẽ bị thu hồi, tôi bắt đầu từ đâu?” | Phân biệt tin dự án với hồ sơ thu hồi; biết thông tin nào cần đối chiếu, không bị suy đoán thửa đất |
| Vừa nhận giấy | “Giấy này là thông báo hay quyết định? Tôi cần đọc gì?” | Biết tên, ngày, cơ quan, nội dung cần xem; không cần upload hoặc cung cấp thông tin định danh |
| Đang kiểm kê/xem phương án | “Danh sách ghi thiếu cây hoặc tài sản, tôi cần tìm hiểu bước nào?” | Hiểu vấn đề cần đối chiếu, loại thủ tục liên quan và nguồn hướng dẫn đã duyệt |
| Chuẩn bị di chuyển | “Chưa rõ chỗ ở mới, tôi cần hỏi những gì?” | Hiểu điều kiện chung và danh sách câu hỏi có ích; không được hứa suất tái định cư |
| Không đồng ý | “Tôi thấy phương án chưa đúng nhưng không biết hỏi ai.” | Phân biệt xin giải thích, góp ý, khiếu nại và tuyến cần trợ giúp; không tự chọn thủ tục khi thiếu dữ kiện |
| Người thân hỗ trợ | “Tôi muốn giải thích lại cho bố mẹ dễ hiểu.” | Câu ngắn, từ quen thuộc, bản đọc nhanh vẫn giữ đủ điều kiện và mở được căn cứ |

Không thiết kế theo giả định người dùng biết phân biệt quyết định thu hồi, quyết định phê duyệt phương án, thông báo chi trả và biên bản kiểm kê. Không yêu cầu họ tự xác định quy định hiện hành hoặc cơ quan giải quyết.

## Phạm vi

Ưu tiên hướng dẫn chung có xuất xứ về trình tự, giấy tờ, điều kiện cần đối chiếu, cơ quan và kênh liên hệ chính thức, quyền phản ánh/khiếu nại trong quá trình thu hồi đất phục vụ Vành đai 4 tại Hà Nội. Giải thích khái niệm và nguồn tổng quan dự án khi giúp hoàn thành những việc đó.

Không xác nhận quyền lợi cá nhân, tính tiền, tra ranh giới/thửa đất, nhận hồ sơ tải lên, soạn đơn cá nhân hoàn chỉnh, nộp thay, gửi email, đặt lịch hoặc theo dõi hồ sơ. Không suy rằng người dùng đã chọn một thủ tục chỉ vì họ dùng từ “kiện”. Nếu hỏi về khởi kiện mà chưa đủ nguồn trong phạm vi, giải thích giới hạn và hướng tới trợ giúp chuyên môn có nguồn, không đưa chiến lược tố tụng hoặc thời hạn từ trí nhớ.

## Cấu trúc trải nghiệm

| Vùng | Nội dung chính | Vai trò |
|---|---|---|
| Bắt đầu | “Bạn đang vướng việc gì?”, các tình huống, ô nhập tự do | Giảm việc phải tự nghĩ câu hỏi pháp lý |
| Hội thoại | Điều đã hiểu, câu trả lời, việc có thể làm tiếp, một câu hỏi cần làm rõ | Luồng chính |
| Hướng dẫn theo việc | Điểm vào về giấy tờ, phương án, chỗ ở mới, ý kiến/khiếu nại | Điều hướng tới nội dung đã duyệt hoặc điền câu hỏi; không tạo pipeline thứ hai |
| Nguồn và nơi liên hệ | Thư viện theo nhu cầu; phân biệt văn bản, thủ tục, đầu mối và tài liệu chỉ tham khảo | Tự đối chiếu và tiếp tục khi AI không khả dụng |
| Đã trao đổi | Lịch sử trên thiết bị và nút xóa | Xem lại trong TTL hiện có |
| Thông tin về trợ lý | Phạm vi, dữ liệu, giới hạn, đánh giá và archive | Minh bạch, đặt ngoài luồng hỏi đáp chính |

Giữ token, font Be Vietnam Pro, theme, kích thước chữ, focus, drawer và khả năng đọc ở 320 px theo Figma hiện có. Thay kiến trúc thông tin, microcopy và nội dung; không tự đổi phong cách thị giác. Thiết kế chi tiết màn hình mới trên cùng file Figma, giữ các frame cũ để đối chiếu. Tài liệu này chưa tạo mockup hoặc handoff Figma mới.

## Các hành trình cần thiết kế

| Hành trình | Tương tác | Điều kiện kết thúc |
|---|---|---|
| Chưa biết hỏi gì | Chọn tình huống hoặc “Tôi chưa rõ”; xem câu hỏi được điền và chỉnh trước khi gửi | Hiểu một vấn đề cụ thể, không bị gửi tự động |
| Mới nhận giấy | Hỏi tên giấy đang nhìn thấy; có “không biết”; hướng dẫn tìm tên/ngày trên giấy thay vì xin ảnh | Xác định loại thông tin cần đọc, hoặc thừa nhận chưa xác định |
| Cần giấy tờ | Phân biệt giấy cần để trao đổi với giấy bắt buộc để nộp thủ tục; mở từng mục và nguồn | Có danh sách đúng nhánh hoặc biết còn thiếu thủ tục nào để lập danh sách |
| Cần nơi hỏi | Hỏi địa bàn mức xã/phường và mục đích; không xin số nhà/thửa | Chỉ ra đầu mối đúng chức năng/thời điểm, hoặc mở trang tra cứu chính thức khi chưa đủ chứng cứ |
| Không đồng ý | Hỏi chưa đồng ý với nội dung/giấy nào và đã ở giai đoạn nào | Biết các hướng tìm hiểu và giới hạn; không nhầm góp ý với khiếu nại hoặc tự kết luận hết thời hạn |
| Hỏi tiếp/sửa thông tin | Giữ dữ kiện đã cung cấp; xác nhận thay đổi có ảnh hưởng; tra cứu lại | Không dùng citation cũ làm chứng cứ và không tiếp tục áp dụng dữ kiện đã bị sửa |
| AI gián đoạn | Giữ bản nháp; thư viện còn mở nếu API nguồn sẵn sàng; không phát câu trả lời giả | Người dùng hiểu trạng thái và tự chọn tiếp tục |

Mỗi lần hỏi làm rõ chỉ hiển thị một câu chính, tối đa ba lựa chọn và lựa chọn không biết. Hai lượt làm rõ liên tiếp mà vẫn thiếu cùng dữ kiện thì dừng vòng hỏi: nêu điều đã giải thích được và chỗ cần đọc trong giấy hoặc nguồn cần mở. Người dùng có thể quay lại sửa lựa chọn.

## Contract nội dung câu trả lời

| Phần | Yêu cầu |
|---|---|
| Trả lời điều đang vướng | 1–2 câu trực tiếp, có nguồn nếu là nội dung pháp lý; không mặc định mở đầu “Đã đối chiếu các căn cứ dưới đây” |
| Giải thích dễ hiểu | Chỉ giải thích thuật ngữ thực sự cần; diễn giải phải nằm trong draft được verify |
| Việc có thể làm tiếp | Tối đa ba việc ưu tiên; mỗi nghĩa vụ, giấy bắt buộc, nơi nộp, phí hoặc thời hạn là claim có nguồn riêng |
| Điều còn chưa xác định | Nêu đúng khoảng trống; không khái quát “chưa đủ căn cứ” nếu đã có câu trả lời chung hữu ích |
| Hỏi thêm | Một câu có mục đích, có thể bỏ qua; không hỏi luật/số điều người dùng phải tự tìm |
| Căn cứ | Citation cạnh nội dung; nhãn nguồn dễ hiểu, mở đúng đoạn và nguồn gốc; metadata kỹ thuật mở rộng |

Không bắt mọi câu trả lời phải có đủ sáu phần. Câu đơn giản nên ngắn; câu nhiều nhánh có thể dài để giữ điều kiện. Mục tiêu biên tập ban đầu là khoảng 150–250 từ cho lượt thông thường, không phải hard cap cắt mất ngoại lệ. Không suy điểm dễ hiểu tiếng Việt từ một ngưỡng readability tiếng Anh.

Ví dụ cấu trúc cho câu “Tôi vừa nhận giấy về Vành đai 4, cần chuẩn bị gì?”:

> Để tìm đúng hướng dẫn, trước hết cần biết tên giấy bạn đang có. Bạn có thể đọc dòng tiêu đề, không cần gửi ảnh hay thông tin cá nhân.
>
> Trên giấy ghi tên nào: “Thông báo thu hồi đất”, “Quyết định thu hồi đất”, hay tên khác/không rõ?

Đây là ví dụ câu hỏi định hướng, không phải checklist pháp lý. Sau khi biết loại giấy, phần giải thích và giấy tờ cần nộp chỉ xuất hiện khi có nguồn đã duyệt cho đúng thủ tục. Không viết sẵn một ví dụ pháp lý chi tiết rồi xem đó là gold.

## Hỏi làm rõ vừa đủ

| Dữ kiện | Khi cần hỏi | Khi không hỏi |
|---|---|---|
| Giai đoạn/tên giấy | Câu trả lời phụ thuộc bước đang xử lý | Câu hỏi định nghĩa hoặc quy định chung |
| Xã/phường, tên cũ nếu có | Cần đầu mối, địa bàn hoặc nguồn địa phương | Giải thích một thuật ngữ chung |
| Ngày quyết định/phương án | Kiểm tra chuyển tiếp, thẩm quyền/thời hạn | Không ảnh hưởng câu trả lời đang hỏi |
| Nhóm đất/giấy tờ | Cần phân biệt điều kiện chung | Không dùng để mở hồ sơ quyền lợi cá nhân |
| Loại bất đồng | Phân biệt yêu cầu giải thích, góp ý, khiếu nại | Không mặc định yêu cầu “khiếu nại lần đầu” |

Không hỏi họ tên, CCCD, số điện thoại, số thửa, địa chỉ nhà chính xác, mã hồ sơ hoặc ảnh giấy tờ. Redaction hiện có chỉ là phòng ngừa theo mẫu, không phải bảo đảm ẩn danh. Nếu người dùng nhập định danh, không lặp lại chúng trong đáp án và không ghi log.

## Ngôn ngữ và độ tin cậy

Ưu tiên câu “Bạn có thể đối chiếu…” khi đó là việc tùy chọn, “nguồn quy định…” khi mô tả nghĩa vụ, “chưa xác định…” khi thiếu dữ kiện. Không đổi “có thể” thành “được”, “một trong” thành “tất cả”, “trường hợp thuộc…” thành quy tắc chung. Mở rộng “Ủy ban nhân dân” khi cần nhưng giữ khác biệt với “Chủ tịch Ủy ban nhân dân”.

“Có căn cứ” không đồng nghĩa “hồ sơ của bạn đủ điều kiện”. Nhãn theo lượt đề xuất là “Quy định chung có nguồn”, “Cần làm rõ”, “Chưa có nguồn phù hợp”, “Dịch vụ tạm gián đoạn”. Không dùng màu xanh hoặc dấu tick khiến người đọc tưởng đã được duyệt quyền lợi. Nhãn chính xác phải kiểm thử hiểu biết với người dùng.

Đánh giá kỹ thuật và trace để ở chi tiết. Bỏ vai trò dẫn dắt của điểm kỷ lục lịch sử trong phiên bản mới; trang minh bạch ưu tiên kết quả đúng cấu hình và phạm vi đã đo. Archive vẫn đầy đủ. Đây là thay đổi đề xuất cho v2, chưa sửa hành vi dashboard hiện hành.

Chính sách snapshot hiện hành được giữ trong đợt thiết kế: không tự khôi phục banner đã bỏ hoặc đổi cờ vận hành. V2 không được gọi thông tin là “hiện hành” chỉ vì generation được bật. Hiển thị mốc nguồn thực tại phần nguồn/thông tin trợ lý, phân biệt mốc xem xét với ngày rà soát; hướng dẫn liên hệ/thời hạn thiếu freshness sẽ bị chặn theo policy nguồn ở thiết kế hệ thống.

## Tiêu chí trải nghiệm

Người dùng bắt đầu mà không biết số hiệu văn bản; chọn “không biết” vẫn đi tiếp được; không phải cung cấp định danh; hiểu bước tiếp theo và điều chưa thể kết luận. Người dùng mở được nguồn đúng câu, thao tác bằng bàn phím, đọc trên mobile có bàn phím ảo và xem lại sau reload trong TTL. Những tiêu chí này cần quan sát và chấm theo kế hoạch EVALUATION, không xác nhận bằng screenshot đẹp.
