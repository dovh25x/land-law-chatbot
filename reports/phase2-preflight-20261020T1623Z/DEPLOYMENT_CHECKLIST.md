# Deployment readiness — chỉ đọc, không triển khai

## Identity

| Thành phần | Bằng chứng hiện tại |
|---|---|
| HEAD local | `117e7bd2c4a320c3d02256dfdabf858180b47dbf`; working tree có F01/F03 chưa commit và report các attempt; không reset/push |
| SQLite candidate | `2dab4dde69323ce35e9732748df40ce15c371d6380d694137a65faf05eccc179` |
| PostgreSQL candidate | `c5008efb7d44adb552371982cdc122b08f7bc3d5656cb8d2ba8362f56f743bda`; fingerprint tính từ code/settings, **chưa deploy/đo model** |
| Live GET | `83f93f6482ed90765a62c39c818d5972e3560e2a2357efa21cd55f13be603b9e`; khác candidate, không xác nhận F01/F03 đã triển khai |
| Corpus local/live | Cùng `corpus-a26bc99e541fbbe2`; live60 documents, phạm vi ring4 |
| SHA cloud | Chưa truy vấn control plane vòng này. Báo cáo cũ ghi `d2424ed…`; không coi là xác nhận SHA hiện tại |

## Checklist

- [x] Backend399 trước sửa Phase2;403 sau sửa trên Python3.14.4 và Python3.12.15.
- [x] Python3.12 dùng venv `/tmp/landlaw-phase2-py312`, cài đúng72 package requirements.lock; không đổi `.venv`/lock/dependency. Thử offline thiếu cache rồi tải package công khai qua cơ chế thực thi được phép, giữ cả log.
- [x] Frontend unit14/build/Playwright100 desktop+mobile với local API fixtures. Không phải public E2E.
- [x] Audit offline60docs/7.392chunks/133raw files; parser60/60, không lỗi/thiếu gold.
- [x] GET public `/`200. Bốn backend GET đầu timeout20s; lần theo dõi sau health531ms, ready1946ms, status1733ms, evaluation1356ms đều200. Phù hợp khả năng cold start, chưa chứng minh nguyên nhân bằng log nền tảng.
- [x] Live readyz báo PostgreSQL/key configured/corpus; **không chứng minh quota hoặc chat thành công**.
- [x] Live status: generation_available=true, source_fresh=false; archive không khớp active runtime/corpus. Không đổi cờ snapshot để làm readiness đạt.
- [x] Review code signed ingress HMAC(method/path/query/time/IP/body hash),60s window; Turnstile hostname/action; quota public; timeout90s; IndexedDB7ngày. Unit/integration kiểm tra các nhánh này.
- [ ] Direct Render negative ingress: chưa đo mới, không giả chữ ký hoặc đọc/ghi secret để thử.
- [ ] CORS/env deployment, DB runtime role và backup/restore mới: chưa kiểm chứng trực tiếp cloud; code/evidence lịch sử không đủ để đánh dấu passed cho candidate.
- [ ] Hard512MiB/image check: Docker CLI WSL không dùng được; chưa build/pull/run image candidate.
- [ ] Public Turnstile→chat→citation→follow-up→reload→delete: chưa làm, vì sẽ tạo session/gọi model và vượt phạm vi read-only.

## Manual public E2E sau approval

| Bước | Nghiệm thu/evidence |
|---|---|
| Mở website | Desktop/mobile thực, không lỗi JS/overflow; UTC/URL/SHA/fingerprint/corpus; ghi cold/warm |
| Turnstile | Người dùng hoàn thành challenge thật, hostname/action hợp lệ; không log token/key hoặc bypass |
| Gửi câu hỏi giả lập ngoài S06 | Câu hỏi không PII được chốt, request budget rõ. Source-fact kiểm tra trước nhưng vẫn cần một lượt LLM được phép riêng để chứng minh provider path |
| Phản hồi | SSE kết thúc có result.status, không draft trước verify; quota/lỗi có phục hồi, không loop retry |
| Citation | Source/excerpt/điều/khoản/trang/link chính thức đúng; khớp chuỗi không thay review nội dung |
| Follow-up | Client history đúng contract, không là chứng cứ; không gọi server history đã ngừng |
| Reload | IndexedDB giữ nội dung/citation/trace tại trình duyệt, dọn sau7ngày; server không giữ conversation payload |
| Xóa | Xóa một cuộc rồi tất cả, reload không xuất hiện lại; không dùng dữ liệu thật |

Review working tree → commit SHA khi được phép → CI Python3.12/frontend/image → rà receipts → approval deploy → đối chiếu SHA/fingerprint/corpus live → manual public E2E được phép. Giữ rollback; restore vào DB riêng, không drop/restore đè serving. Profile học thuật và quality gates fail phải công bố trung thực.
