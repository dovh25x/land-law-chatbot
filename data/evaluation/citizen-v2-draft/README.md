# Tình huống đánh giá người dân — bản dự thảo

Đây là dữ liệu thiết kế cho [chương trình đánh giá v2](../../../docs/redesign/EVALUATION.md): 48 câu phát triển theo sáu nhóm và tám kịch bản hành trình. Nội dung được viết để chuẩn bị annotation, không phải kết quả nghiên cứu người dùng hoặc bộ gold pháp lý.

`manifest.json` ghi `draft_not_frozen`, `execution_ready=false`, số ca và hash các file. Hash chỉ giúp nhận diện bản nháp; **không phải freeze được phê duyệt**. Không thêm vào ba split đang chạy và không sửa freeze của smoke/supplemental/natural.

| File | Nội dung |
|---|---|
| `scenarios.jsonl` | Câu hỏi, nhu cầu, yêu cầu nguồn, điều phải có/cấm, policy hỏi làm rõ |
| `journeys.jsonl` | Script tương tác nhiều lượt và hành vi cần đạt; không phải history fixture hay output model |
| `manifest.json` | Identity bản nháp, số ca và công việc trước khi được thực thi |

`source_requirements` trỏ tới C01–C12 trong [kế hoạch corpus](../../../docs/redesign/CORPUS.md). Các mã này không phải document/chunk IDs. Ngày `as_of` là mốc dự kiến cần annotation, không xác nhận nguồn còn hiện hành tại ngày đó.

Trước khi chạy: chốt snapshot, duyệt answerability, required propositions, evidence groups/alternatives, luật/thủ tục/danh bạ thực tế, review pháp lý/nội dung, fixture còn thiếu và khóa phiên bản trước chỉnh prompt. Không điền gold từ đáp án model. P08 cần history fixture để kiểm tra tóm tắt; J07 cần browser harness, J08 cần fixture history vượt cửa sổ context. Những phần đó chưa có implementation trong bản bàn giao này.

CLI hiện tại từ chối split ngoài smoke/supplemental/natural. Cần triển khai registry/evaluator riêng trong một patch sau này. Không gọi bộ này là holdout độc lập; holdout theo kế hoạch chưa được thu thập.
