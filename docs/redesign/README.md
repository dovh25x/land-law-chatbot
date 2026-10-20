# Thiết kế lại trợ lý Vành đai 4 cho người dân

**Trạng thái: thiết kế đích; mã nguồn đã triển khai các phần mô tả trong [IMPLEMENTATION](IMPLEMENTATION.md).** Phạm vi đã chốt với chủ dự án: thiết kế đầy đủ trước, ưu tiên thủ tục, giấy tờ, nơi liên hệ và khiếu nại liên quan Vành đai 4 tại Hà Nội. Tài liệu thiết kế tiếp tục mô tả đích đầy đủ; IMPLEMENTATION phân biệt phần đã có trong code với nguồn, đánh giá và phát hành còn cần hoàn tất.

Quyết định cốt lõi là chuyển từ công cụ trả lời câu hỏi pháp luật sang trợ lý giúp người dân **hiểu tình huống, hiểu giấy tờ và biết việc tiếp theo có thể tìm hiểu hoặc thực hiện**. Người dùng không cần biết tên luật, điều khoản hay cơ cấu cơ quan để bắt đầu. Mọi hướng dẫn có hệ quả pháp lý vẫn phải có chứng cứ, đúng đối tượng, thời điểm và ngoại lệ.

| Quyết định | Thiết kế mới |
|---|---|
| Có làm lại toàn bộ hệ thống không? | Thiết kế lại sản phẩm, contract nội dung, tổ chức nguồn và cách đo thành công. Giữ nền tảng kỹ thuật còn phù hợp; triển khai từng patch có hồi quy, không viết lại toàn bộ agent. |
| Có làm lại bộ đánh giá không? | Làm một chương trình đánh giá mới theo tác vụ người dân. Giữ nguyên 20+4 và natural đã khóa để kiểm tra lỗi cũ; chúng không còn là thước đo đầy đủ cho sản phẩm mới. |
| Có làm lại corpus không? | Rà soát và tổ chức lại theo nhu cầu, bổ sung nguồn thủ tục/danh bạ chính thức. Giữ đoạn và vector còn đúng; không xóa toàn bộ hoặc embedding lại để đổi trải nghiệm. |
| Kết quả cũ xử lý thế nào? | Giữ bằng chứng có phiên bản để truy nguyên. Bỏ khỏi vai trò chứng nhận phiên bản mới nếu khác corpus/backend/fingerprint hoặc không đo đúng tác vụ. Không sửa verdict, checksum hoặc xóa thất bại. |
| Thay model, hosting, pipeline? | Giữ FastAPI/LangGraph/Groq GPT-OSS 120B, E5 ONNX Q8 384 chiều và hosting Free. Không thêm reranker, fine-tuning, multi-agent hoặc GIS. |
| Phạm vi mới đến đâu? | Hướng dẫn có nguồn về thủ tục, giấy tờ, đầu mối và khiếu nại trong quan hệ với thu hồi đất, bồi thường, hỗ trợ, tái định cư của Vành đai 4 Hà Nội. Không mở thành chatbot mọi vấn đề pháp luật hay kênh tin tức dự án. |

## Bộ bàn giao

| Tài liệu | Nội dung |
|---|---|
| [Sản phẩm và trải nghiệm](PRODUCT.md) | Tác vụ, hành trình, hỏi làm rõ, mẫu trả lời, màn hình và tiêu chí dễ hiểu |
| [Thiết kế hệ thống](SYSTEM.md) | Thay đổi trong cùng graph, contract request/result, kiểm chứng hành động và phân quyền dữ liệu |
| [Kế hoạch corpus](CORPUS.md) | Ma trận nhu cầu–nguồn, giữ/loại/bổ sung, freshness, provenance và tái sử dụng embedding |
| [Đánh giá phiên bản mới](EVALUATION.md) | Regression cũ, bộ phát triển mới, hành trình, holdout, người dùng thật và rubric |
| [Lộ trình triển khai](ROADMAP.md) | Thứ tự thực hiện, file chịu ảnh hưởng, điều kiện hoàn tất, rủi ro và rollout |
| [Câu hỏi phát triển dự thảo](../../data/evaluation/citizen-v2-draft/scenarios.jsonl) | Các câu hỏi tiếng Việt đời thường, yêu cầu nguồn và tiêu chí hành vi; chưa có gold pháp lý được duyệt |
| [Hành trình dự thảo](../../data/evaluation/citizen-v2-draft/journeys.jsonl) | Hội thoại nhiều lượt theo kịch bản, sửa dữ kiện và tình huống gián đoạn |
| [Báo cáo khảo sát repository](../../reports/redesign-discovery-20261019/README.md) | Phát hiện, giới hạn khảo sát và inventory gắn checksum của source tham chiếu |

## Những thay đổi có ý nghĩa nhất

Trang mở đầu hỏi “Bạn đang vướng việc gì?” với các lối vào theo tình huống: mới nghe tin thu hồi, vừa nhận giấy tờ, đang xem phương án, cần hiểu chỗ ở mới, chưa đồng ý với nội dung, cần tìm nơi hỏi. Ô nhập tự do luôn có sẵn và có lựa chọn “Tôi chưa rõ”. Đây là tổ chức thông tin mới trên nền typography, màu và component Figma đã thống nhất; bố cục mới cần handoff trước khi code UI.

Đáp án ưu tiên điều người dân cần hiểu, giải thích thuật ngữ ngay khi xuất hiện, rồi đưa tối đa vài việc tiếp theo có căn cứ. Nguồn mở tại đúng câu hoặc hành động. Không bắt người dân đọc trace, checksum hoặc nhớ số điều mới sử dụng được ứng dụng.

Hỏi thêm phải giúp tiến tới câu trả lời: hỏi một câu quan trọng tại một thời điểm, có “không biết”, không hỏi lại dữ kiện đã cung cấp. Khi chưa đủ thông tin để nhận định quyền lợi cá nhân, vẫn có thể giải thích quy định chung đã truy xuất và kiểm chứng. Không biến hỏi lại thành vòng thu thập hồ sơ mà hệ thống không thể thẩm định.

## Cách đọc và thực hiện

Đọc PRODUCT trước SYSTEM, sau đó chốt ma trận nguồn trong CORPUS và annotation trong EVALUATION trước khi chỉnh prompt. ROADMAP chuyển từng quyết định thành patch có thể review. Chưa lấy bản thiết kế này làm bằng chứng hệ thống đã tốt hơn; điều đó phải được đo trên cấu hình triển khai và với người dùng mục tiêu.

Các nguyên tắc tác vụ và ngôn ngữ tham khảo [GOV.UK về nhu cầu người dùng](https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs) và [viết nội dung giao diện](https://www.gov.uk/service-manual/design/writing-for-user-interfaces). Đây là tài liệu phương pháp; không chứng minh các giả thuyết về người dân Vành đai 4. Cần kiểm chứng bằng nghiên cứu người dùng Việt Nam theo kế hoạch đánh giá.
