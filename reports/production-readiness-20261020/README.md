# Phát hành cho người dân — 20/10/2026

Đợt này triển khai phần mềm trong profile `academic` / `academic_prototype` hiện hành. Không chứng nhận pháp lý hoặc tuyên bố hoàn thành chất lượng sản phẩm v2. Trạng thái deployment/live sẽ được ghi khi có kết quả thật.

- [Profile và điều kiện phát hành](RELEASE_PROFILE.md); [miễn trừ do chủ dự án yêu cầu](acceptance-waiver.json). Reviewer pháp lý độc lập và nghiên cứu người dùng chưa được thực hiện; không ghi là passed.
- [Phục hồi PostgreSQL và quyền runtime](postgres-runtime-and-restore.json), [tải lại Release](release-download.json), [cấu hình trước rollout](render-config-preflight.json). Database phục vụ và active corpus giữ nguyên; không tạo lại embedding, không gỡ Release cũ.
- [Rà soát nguồn](source-review.json): candidate chỉ là tham khảo pending; chưa đủ chứng cứ để chỉ nơi nộp hồ sơ hoặc checklist. Mốc nguồn cũ và khoảng trống corpus vẫn tồn tại, không có freshness receipt mới.
- Kết quả natural giữ riêng theo fingerprint: [attempt đầu](natural-attempt-1/reviewed/natural/results.md), [prompt gọn](prompt2-evaluation/reviewed/natural/results.md), [guard nhóm giao khoán](final-guard-check/reviewed/natural/results.md). Không ghép pass giữa các cấu hình, không đổi gold hoặc ngưỡng. Rà soát bằng AI theo rubric và snapshot, không phải thẩm định độc lập.
- [Phạm vi được phép gọi Groq](evaluation-authorization-status.json): chủ dự án đã cho phép đủ 32 câu sau lần từ chối mở rộng trước đó. Hạn mức TPD thật của Groq đang làm đợt chạy mới phải giữ checkpoint và chờ; chưa coi ca chưa chạy hoặc limited là đạt.

Bộ v2 gồm tình huống/journey dự thảo chưa freeze, chưa chấm. Fixture pass, citation integrity và việc chặn một draft sai không chứng minh hệ thống đã giải quyết đúng mọi vấn đề của người dân. Từ chối trên câu có nguồn vẫn là không đạt tác vụ.

Giữ deployment trước rollout trong `before-live.json` và `cloudflare-before.json` để rollback ứng dụng. Rollback không khôi phục hội thoại trên server hoặc corpus đa dự án. Phục hồi corpus chỉ trên database riêng.
