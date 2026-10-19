# Hoàn thiện sản phẩm — 2026-10-19

Theo chỉ đạo mới của chủ dự án, bỏ rubric/điểm đánh giá nội dung khỏi điều kiện chặn publish/deploy mặc định. Không chuyển kết quả chất lượng cũ thành passed và không tạo receipt nguồn giả.

## Thay đổi

- Thư viện hiển thị nguồn đã lập chỉ mục và bản gốc tham khảo trong phạm vi; tìm tiếng Việt không dấu, mở PDF chính thức. Tám nguồn pending được truy cập bản gốc, không tự trở thành chứng cứ AI. Không đổi active corpus, chunk hoặc embedding.
- Phiên hết hạn khôi phục bản nháp, bỏ token cũ và yêu cầu gửi lại chủ động. Session vẫn dùng được trong tab khi sessionStorage bị chặn; widget challenge có thể tải lại sau lỗi. Trạng thái Groq được làm mới khi hết cooldown hoặc tab trở lại.
- Verifier phân biệt khoản đang đọc và khoản được dẫn chiếu; structural guard giữ đúng địa bàn nơi có đất thu hồi. Claim/citation vẫn phải qua kiểm chứng.
- Publish có quality opt-in; deploy ghim source đã commit, giữ hosting Free, theo dõi/resume đúng Render deployment. Preview Pages dùng branch riêng. Workflow deploy nhận SHA và không yêu cầu readiness rubric.
- Sửa đường dẫn import pytest trong CI, bỏ side effect dotenv khi import helper; cập nhật secret runtime DB/API key và các biến GitHub Actions. Workflow vận hành tôn trọng chế độ snapshot được chủ động bật nhưng giữ warning freshness.
- Sửa chỗ E2E ghi đè ảnh report cố định; xuất lại ba diagram bằng diagram-design revision đã ghim và kiểm tra trực quan.

## Kiểm chứng phần mềm

Source sản phẩm đã kiểm thử: `c880baf68c6f2c8926104d1b32397ab8ada2fe6a`. Source triển khai: `b8f2953c8c329a2670e5669d1091ff7862b874a5`; chỉ khác workflow Wrangler và tài liệu. Fingerprint PostgreSQL: `cc345ca773ec6f9deb57106c37db6827b462ebf0c503e86cdd1a4400f8b10598`.

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Backend | 257 passed | backend-tests-release.log |
| Frontend unit | 7 passed | frontend-unit-attempt-1.log |
| Frontend build | Thành công | frontend-build-attempt-1.log |
| E2E trước ca bổ sung | 70 passed | frontend-e2e-attempt-1.log |
| E2E bổ sung desktop/mobile | 8 passed | frontend-product-cases-attempt-3.log |
| npm audit | 0 vulnerabilities | frontend-audit.log |
| Secret scan source | Passed | secrets-final-source.log |
| Ba diagram | Self-check OK và xem trực quan | diagram-self-check.log |
| PDF tham khảo | 8/8 HTTP 206, header PDF | reference-links-attempt-1.json |

CI trên SHA cuối đã đạt cả backend, frontend và Docker memory 512 MiB: checks-run.json/log. Workflow Runtime metadata checks trên database thật đã đạt: operations-run.json/log. Kiểm tra PDF chỉ chứng minh truy cập và định dạng, không chứng minh hiệu lực pháp lý.

## Những attempt được giữ

- backend-tests-attempt-1.log: lỗi môi trường do import helper tự load dotenv; sửa side effect, attempt 2 đạt 256 ca.
- frontend-product-cases.log: fixture cooldown chỉ trả limited một lần, bị mount/focus tiêu thụ; đổi fixture giữ trạng thái đến khi test chủ động kết thúc cooldown.
- frontend-product-cases-attempt-2.log: máy chủ local không mở được trong sandbox; attempt 3 ngoài sandbox đạt.
- backend-tests-final.log: TestClient treo trong sandbox, đã dừng đúng tiến trình. backend-tests-final-escalated.log: fixture mới thiếu vector/embedded, validator từ chối đúng; sửa fixture, regression riêng và bộ cuối đều đạt.
- CI commit trung gian 1414f52 giữ lỗi fixture vừa nêu. Workflow deploy 39208181105 bị hủy do nhập nhầm tham số SHA, chưa tạo deployment; workflow đúng SHA là 39208203032 nhưng backend bị chặn đúng do Wrangler action đã sửa package/lockfile sau test. Thay action cài dependency vào checkout bằng npx dùng cache tạm; workflow tiếp theo là 39208524230.

## Phạm vi và giới hạn

Generation được bật với snapshot override; checked_at không được làm mới giả. Không chạy lại bộ model/rubric đầy đủ làm điều kiện phát hành theo yêu cầu của chủ dự án. Báo cáo nội dung trước đây vẫn giữ nguyên, không được xem là chứng nhận cho fingerprint mới. Các PDF pending vẫn cần OCR/đối chiếu trước khi có thể đưa vào chỉ mục chứng cứ; hiện người dùng mở bản gốc trong thư viện. Không tự động vượt Turnstile để chứng minh chat public trong trình duyệt. Không bỏ quota, giới hạn Groq, verify, provenance hoặc quyền riêng tư.

Bản corpus đang dùng là corpus-a26bc99e541fbbe2, 60 tài liệu/7.392 chunk; thư viện bổ sung 8 bản gốc tham khảo. Asset corpus và database rollback được giữ nguyên.

## Production đã xác minh

- URL: https://hanoi-land-law.pages.dev
- Deployment ứng dụng: `b8f2953c8c329a2670e5669d1091ff7862b874a5`, Render `dep-dbar9rc9v7es739l8qag` live; Pages `897238b0-abe5-4ab8-9900-d86545eb7af7` success.
- CI cuối: [39208511672](https://github.com/dovh25x/land-law-chatbot/actions/runs/39208511672), deploy: [39208524230](https://github.com/dovh25x/land-law-chatbot/actions/runs/39208524230), giám sát: [39208208434](https://github.com/dovh25x/land-law-chatbot/actions/runs/39208208434). Tất cả success.
- `public-runtime.json`: corpus/fingerprint khớp, generation_available=true, source_fresh=false đúng snapshot override; unsigned backend 403.
- `product-live.json`: cả 1440/390/320 px đạt, tìm không dấu, mở đúng PDF NĐ 281/2026, reference không có chunk chứng cứ và không tràn ngang.
- `workflow-evidence/`: receipt Render nối tiếp, báo cáo navigation thực và ảnh desktop/mobile từ CI. Đã xem trực quan ảnh desktop và mobile; chat Turnstile không được tuyên bố đã đạt.
- `render-config-comparison.json`: Groq key và database khớp cấu hình operator, generation và snapshot override bật; không có owner credential trên Render. File chỉ chứa boolean.
- Không thay asset backup corpus, không xóa database hoặc Release cũ.
