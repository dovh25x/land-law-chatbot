# S06 — một lượt Groq được cho phép, 20/10/2026

**Kết quả: FAIL cho mục tiêu trả lời S06; từ chối an toàn hoạt động.** Không chạy lại.

- HEAD: `117e7bd2c4a320c3d02256dfdabf858180b47dbf` cùng bản vá Phase 1 chưa commit.
- Runtime fingerprint: `4bae32ade64cc02359381fc214c91a14f1b623c8f0a00235cbe70109da47a98b`.
- Model: `openai/gpt-oss-120b`; corpus: `corpus-a26bc99e541fbbe2`; as_of: `2024-08-02`.
- SQLite tạm riêng; dùng `scripts/evaluate_generation_candidate.py` và harness hiện có, lọc duy nhất S06.
- 1 attempt, 2 HTTP 200 requests: draft và một repair trong cùng lượt; không có transport retry hoặc LLM verifier request.
- 6.431 giây cho lượt agent; 5.805 prompt tokens + 2.201 completion tokens = 8.006 total tokens theo usage Groq. Không phải số đo HTTP/cloud hoặc p95.
- Retrieval giữ 4 passages gồm parent/leaf; prompt gửi 3 passages công khai ở Điều 95, không gửi toàn corpus. Không gửi history hay dữ liệu cá nhân. Header xác thực không được lưu.
- Kết quả cuối `insufficient_evidence`, 0 verified claims, 0 citations. Citation accuracy không áp dụng, không được tính pass.

## Đối chiếu nguồn

[Luật 31/2024/QH15, Điều 95, bản Công báo chính thức](https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/31-2024-qh15_2.pdf#page=5), trang PDF 5–7, trang Công báo 6–8: khoản 1 nêu các nhóm đối tượng/trường hợp; khoản 2 đặt các điều kiện thay thế cho các trường hợp thuộc khoản 1. Giấy chứng nhận là một phương án trong khoản 2, không đủ để bỏ qua phạm vi khoản 1.

Cả hai draft bỏ prerequisite thuộc khoản 1 dù context đã chứa phần này. Repair liệt kê các điểm a–đ nhưng vẫn không giữ prerequisite. Lượt này không gán tường minh các giấy tờ cho khoản 1; chưa thể kết luận model đã phân biệt đúng hai khoản. Structural verifier chặn cả hai draft trước khi gọi LLM verifier; draft không được phát ra người dùng.

Guard còn báo lỗi phụ về AND vì bắt cụm “còn phải có”, trong khi repair viết “còn phải có một trong”. Đây là dấu hiệu false positive trong guard, không phải bằng chứng model biến OR thành AND. Lỗi thiếu phạm vi đối tượng độc lập vẫn đủ để từ chối. Chưa sửa guard hoặc prompt.

## Bằng chứng

- `execution-receipt.json`: số request, observer và xác nhận protected inputs không đổi.
- `execution-scope.json`, `execution-runner.py`: phạm vi và instrumentation chỉ quan sát, không sửa payload/return value.
- `protected-inputs-before.json`, `protected-inputs-after.json`: checksum runtime/tests, evaluation và snapshot trước/sau.
- `runs/`: metadata, records, summary, immutable attempt và structured model outputs theo harness hiện có. Summary vẫn giữ mẫu số suite 20 ca, chỉ hoàn thành 1 ca.
- `retrieval/`: đoạn luật đã lấy; `wire/requests/`: request JSON công khai không có headers; `wire/responses/`: status, usage và rate limit, không có provider error body/hidden reasoning.
- `verification/`: verdict thực tế sau từng draft; `reviews.json`: nhận xét fail gắn answer checksum; `technical-review.json`: đối chiếu và giới hạn.
- `operator-cooldown.json`: giữ cooldown quan sát được; không reset để chạy lại.

## Bước tiếp theo đề xuất, chưa thực hiện

Giữ F03 mở trong Phase 1. Cần thiết kế cách trình bày continuation và prerequisite theo nguồn cho synthesis, kèm regression tổng quát. Xem xét false positive OR/AND riêng bằng ca dương/âm, giữ nguyên yêu cầu citation verification. Cần phê duyệt mới trước sửa hoặc chạy model lại; chưa chuyển Phase 2.

Không sửa runtime/tests trong lượt này, không thay corpus/model/prompt/verifier/ngưỡng, không thay production/cloud/credentials, không commit/push/deploy. Kết quả một ca SQLite không đại diện benchmark toàn hệ thống hoặc thẩm định pháp lý độc lập.
