# Phát hành cho người dân — 20/10/2026

Phần mềm đã được phát hành lên [production](https://hanoi-land-law.pages.dev), cùng SHA `069d21e8fcdc73161e38f678c95805539c8813cd` trên Render và Cloudflare Pages. Profile giữ `academic` / `academic_prototype`. **Đã hoàn tất rollout phần mềm; chưa đạt cổng chất lượng đầy đủ hoặc nghiệm thu sản phẩm v2.**

## Đã xác minh

- [CI đúng SHA](ci-069d21e.json) và [kết quả kiểm tra](software-069d21e.json): 284 backend, 14 frontend unit, 100 E2E; build, secrets scan, audit và Docker/RAM đạt. Image đo peak RSS 392,74 MiB với giới hạn 512 MiB; không phải SLA hoặc chứng nhận pháp luật.
- [Identity production](production-identity.json): Render Free `dep-dbbf4auq1p3s73cd4d10`, Pages `66d937e2-18de-430c-bc51-5034deb63f83`; cùng SHA, bundle frontend khớp, API v3/schema2, corpus và fingerprint đúng. Signed ingress từ Pages hoạt động; gọi API trực tiếp Render bị từ chối. Runtime không có quyền đọc/ghi messages, traces hoặc answer_cache.
- [Browser navigation thật](live-navigation/navigation.json): 1440/390/320 px, thư viện văn bản, nguồn và trang đánh giá; không mock API. Mobile là mô phỏng, không phải thiết bị vật lý. Đã xem trực tiếp ảnh desktop và 320 px.
- [Public controls](live-public-controls.json): thiếu Turnstile bị chặn, phiên không hợp lệ bị từ chối, server history trả 410. Quota Groq thật được phản ánh bằng `provider_limited`; [chỉ cập nhật metadata cooldown](shared-provider-cooldown.json), không đổi quota hoặc corpus.
- [Restore PostgreSQL và quyền runtime](postgres-runtime-and-restore.json), [tải lại asset Release](release-download.json). Không restore đè database phục vụ, không tạo lại embedding hoặc gỡ Release cũ.

## Đánh giá và phần chưa xác minh

[Biên bản tổng hợp](release-status.json) giữ đủ mẫu số. Cấu hình phát hành có 17/32 ca được thực thi: 16 pass về guard/source-fact không dùng LLM, 1 limited do TPD; 15 ca chưa chạy. **Không có điểm độ chính xác natural thực chất cho sáu câu cần nội dung LLM trên cấu hình này.** Các kết quả cấu hình trước không được chuyển thành pass cho cấu hình hiện tại.

| Bộ hiện tại | Thực thi | Pass | Limited/fail | Chưa chạy | Chi tiết |
|---|---:|---:|---:|---:|---|
| Smoke | 14/20 | 13 | 1 | 6 | [Rà soát](release-candidate-evaluation/review-v1/smoke/results.md) |
| Supplemental | 1/4 | 1 | 0 | 3 | [Rà soát](release-candidate-evaluation/review-v1/supplemental/results.md) |
| Natural | 2/8 | 2 | 0 | 6 | [Rà soát](release-candidate-evaluation/review-v1/natural/results.md) |

Chủ dự án đã [cho phép đủ 32 câu](evaluation-authorization-status.json). Groq báo TPD 200.000, used 198.185 và requested 4.141 tại lần bị chặn gần nhất; [log và toàn bộ checkpoint](release-candidate-evaluation/). Retry-After là thời gian tối thiểu cho yêu cầu bị chặn, không bảo đảm còn đủ token cho cả lượt sáu request. Không đổi key/model, bỏ cooldown hoặc chạy song song để vượt hạn mức. Không có tiến trình benchmark âm thầm tiếp tục cạnh tranh quota với public sau bàn giao.

Có thể tiếp tục đúng checkpoint sau khi provider có đủ dung lượng:

```bash
.venv/bin/python reports/production-readiness-20261020/release-candidate-evaluation/resume_operator.py
```

Lệnh xác nhận fingerprint, dùng lại PostgreSQL đánh giá tách biệt và giữ counters/cooldown; chỉ retry ca error/limited, không chạy lại ca hoàn tất để chọn kết quả đẹp. Mỗi lượt mới cần export/review vào thư mục phiên bản tiếp theo, gắn checksum câu trả lời; không sửa review-v1 hoặc artifact lịch sử. Script không triển khai ứng dụng và không thay database phục vụ.

[Managed Turnstile trong headless browser](live-turnstile.json) không tự tạo token; chưa xác minh được phiên thật và chu trình public LLM/follow-up/IndexedDB trên SHA này. Không dùng test key hoặc tự động checkbox để đổi kết quả thành pass. Thực thi trình duyệt không có conversation payload được lưu vào báo cáo.

## Phạm vi và miễn trừ

[Profile phát hành](RELEASE_PROFILE.md) giữ chính sách rubric tùy chọn hiện hành, không tắt một cổng đang bật. [Miễn trừ của chủ dự án](acceptance-waiver.json) áp dụng reviewer pháp lý độc lập và nghiên cứu người dùng trước phát hành; hai việc đó chưa được làm, không phải passed. Rà soát trong đợt này do AI đối chiếu rubric/snapshot, không phải thẩm định pháp lý độc lập.

[Rà soát nguồn](source-review.json): ba candidate mới chỉ là `reference_only`, không có chunk hoặc hiệu lực đã xác minh. Chưa đủ chứng cứ để chỉ nơi nộp hồ sơ, checklist hoặc đầu mối giải quyết cụ thể. Mốc nguồn cũ và khoảng trống corpus vẫn tồn tại, không có receipt freshness mới. Bộ 48 tình huống và 8 journey v2 vẫn là draft chưa freeze/chấm.

Lịch sử cấu hình được giữ nguyên: [attempt đầu](natural-attempt-1/reviewed/natural/results.md), [prompt gọn](prompt2-evaluation/reviewed/natural/results.md), [guard giao khoán](final-guard-check/reviewed/natural/results.md), [guard số khoản](authority-clause-check/reviewed/natural/results.md). Regression bổ sung chặn lỗi nhóm giao khoán/điều kiện hỗ trợ, gán sai khoản thẩm quyền và biến tình huống chưa bố trí chỗ ở thành điều kiện pháp luật. Fixture pass và citation integrity không thay thế chất lượng tác vụ; abstention trên ca có nguồn vẫn không đạt tác vụ.

Giữ deployment trước rollout trong `before-live.json` và `cloudflare-before.json` để rollback ứng dụng. Rollback không khôi phục hội thoại server hoặc corpus đa dự án. `SHA256SUMS` ghi checksum bằng chứng bàn giao; các checkpoint đang tiếp tục trong tương lai phải được đóng gói bằng phiên bản mới.
