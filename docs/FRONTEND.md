# Frontend và nguồn thiết kế

## Nguồn tham chiếu

[Figma · Vành đai 4](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=4-186), trong team `codex`, chứa các frame tham chiếu ban đầu. Trang [UI UX Redesign](https://www.figma.com/design/0Zlzf91hFOPeWp41veuD7l?node-id=14-2) là handoff cho giao diện mới về bố cục, màu sắc, typography và các trạng thái giao diện. Không dùng screenshot Figma làm asset thay cho implementation.

Các frame ban đầu được giữ nguyên để đối chiếu:

| Màn hình | Frame |
|---|---|
| Desktop sáng | `4:186` |
| Desktop tối | `4:216` |
| Mobile | `4:246` |
| Khởi đầu | `5:8` |
| Nguồn căn cứ | `5:14` |
| Trạng thái vận hành | `5:20` |
| Thư viện văn bản | `7:8` |
| Đánh giá hệ thống | `7:15` |

[Handoff cho người dân](redesign/IMPLEMENTATION.md#handoff-giao-diện) bổ sung trang đầu và làm rõ tên giấy, sáng/tối, desktop/mobile trên cùng hệ thiết kế. Trang đầu hỏi “Bạn đang vướng việc gì?”, có bốn gợi ý ngắn: năng lực của trợ lý; điều kiện bồi thường đất ở khi có sổ đỏ; hỗ trợ khi thu hồi đất nông nghiệp; điều kiện bố trí tái định cư khi phải chuyển nhà. Chọn gợi ý chỉ điền và focus ô nhập, không tự gửi hay hardcode đáp án. Đây là câu hỏi giao diện, không phải evaluation suite. `agentic_rag` production hiện trả `answer_schema_version=1`, nên UI dùng prose renderer; structured claim renderer version 2 chưa hoạt động trong production. `citizen.ts` kiểm tra projection và tạo nội dung sao chép tương ứng. Lịch sử schema cũ tiếp tục đọc được. Phiên bản v2 sai cấu trúc không hiển thị content thay thế.

Bốn câu trong `frontend/src/citizen.ts` đã deploy cùng PR #13 tại SHA `1a9718f03ed261f3511598488ab273b6bf5e0b92`. [Kiểm tra public](../reports/releases/academic-mvp-1a9718f/README.md) xác nhận click chỉ điền/focus trên desktop và mobile emulation; không tự gửi:

1. `Trợ lý này có thể giúp gì?`
2. `Có sổ đỏ, khi Nhà nước thu hồi đất ở thì điều kiện được bồi thường là gì?`
3. `Khi bị thu hồi đất nông nghiệp, người dân có thể được hỗ trợ những gì?`
4. `Nếu bị thu hồi đất ở và phải chuyển nhà, điều kiện được bố trí tái định cư là gì?`

Câu 1 được phân loại là capabilities/social để trả lời giới thiệu năng lực, không kéo retrieval pháp luật. Ba câu còn lại là câu hỏi có điều kiện, không hứa chắc chắn được bồi thường/tái định cư; deterministic test kiểm tra chúng có ít nhất một đoạn admitted trực tiếp trong fixture đã review.

## Nguyên tắc trải nghiệm

Hội thoại là luồng chính, tham khảo cách sử dụng của ChatGPT nhưng giữ tên sản phẩm và tiếng Việt. Thư viện nguồn là điều hướng phụ; trang đánh giá đã được gỡ khỏi UI. Không có lựa chọn model, retrieval mode, dự án, tài khoản, thanh toán hoặc upload hồ sơ.

Typography dùng Be Vietnam Pro, palette trung tính, hỗ trợ light/dark. Cột đọc tham chiếu 760 px, sidebar 264 px và source drawer 420 px trên desktop; source panel chuyển toàn màn hình dưới 768 px. Từ 1280 px, nguồn là vùng `complementary` rộng 420 px và không chặn hội thoại; ở 768–1279 px dùng modal drawer. Header cao 64 px; sidebar có thể thu gọn. Nội dung động phải wrap và cuộn được, không cố định chiều cao theo văn bản mẫu trong Figma.

Citation hiển thị nguồn và locator, mở đoạn căn cứ cùng liên kết nguồn chính thức. Thao tác chi tiết thực thi và sao chép đặt cạnh đáp án. “Xem nguồn” mở danh sách citation của đúng đáp án; chọn citation mở đúng đoạn trích. Metadata phiên bản nguồn nằm trong mục mở rộng. Trace không hiển thị trong UI người dân.

## Cấu trúc implementation

| File/thư mục | Trách nhiệm |
|---|---|
| `frontend/src/App.tsx` | Hội thoại, điều hướng, gửi/hủy và các panel |
| `frontend/src/api.ts` | Phiên, HTTP và parser SSE |
| `frontend/src/history.ts` | IndexedDB, TTL, giới hạn dung lượng và history request |
| `frontend/src/Turnstile.tsx` | Widget xác minh trước khi tạo phiên; chỉ được lazy-load khi có `VITE_TURNSTILE_SITE_KEY` |
| `frontend/src/ui.tsx` | Component thư viện, nguồn và thông tin dữ liệu (`TracePanel` legacy không dùng) |
| `frontend/src/styles.css` | Tokens sáng/tối và responsive layout |
| `frontend/public/figma/` | Asset tĩnh lấy từ thiết kế |
| `frontend/functions/` | Proxy ingress cùng origin |

Simple Design System được dùng làm tham chiếu thiết kế; repo không có package SDS tương ứng, nên implementation dùng component và CSS hiện có. Asset Figma được lưu local; không để URL asset tạm trong runtime.

## Hội thoại và lịch sử

Nội dung và citation được lưu tại trình duyệt theo giới hạn trong [kiến trúc](ARCHITECTURE.md#lưu-trữ-và-quyền-riêng-tư). UI phải nói rõ lịch sử không đồng bộ thiết bị; xóa lịch sử không đặt lại quota phiên API.

Client chỉ gửi các cặp hội thoại hoàn chỉnh trong giới hạn API. Không gửi trace hoặc xem citation cũ là chứng cứ. Sau mất SSE, không tự gửi lại POST chat; giải thích server không lưu kết quả để khôi phục.

Không lưu được IndexedDB phải có thông báo. Không chuyển sang server persistence để che lỗi lưu trữ tại máy.

## Trạng thái bắt buộc

| Trạng thái | Hành vi giao diện |
|---|---|
| Khởi đầu | Giới thiệu phạm vi, gợi ý câu hỏi và composer |
| Đang xử lý | Hiển thị bước thực thi và nút dừng |
| Hỏi làm rõ/thiếu chứng cứ | Hiển thị giới hạn và thông tin cần bổ sung |
| Cold start | Thông báo đang kết nối, không giả định backend đã sẵn sàng |
| Quota/provider giới hạn | Giải thích giới hạn thực tế và thời gian chờ khi có |
| Nguồn quá hạn/generation tắt | Giữ thư viện nguồn truy cập được |
| Mất kết nối/hủy | Không ngụ ý có thể lấy lại đáp án từ server |
| Lỗi lịch sử | Nêu rõ dữ liệu chỉ còn trong tab |
| Báo cáo khác phiên bản | Hiển thị cảnh báo corpus/fingerprint |
| Challenge tắt (`SESSION_CHALLENGE_MODE=disabled`) | Không render widget, không tải script; gửi câu hỏi tạo phiên ẩn danh trực tiếp |
| Turnstile yêu cầu tương tác (chỉ khi bật) | Cho phép người dùng hoàn tất challenge, không bypass |

## Kiểm tra thay đổi

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Đối chiếu Figma trên desktop/mobile và cả hai theme, gồm chiều rộng cột đọc, hierarchy, source panel, citation và composer. Kiểm tra Tab/Escape, focus sau đóng panel, thông báo qua role phù hợp, văn bản dài và không tràn ngang ở 320 px.

E2E fixture kiểm tra gửi/hỏi tiếp, session không đổi khi tạo cuộc mới, reload, xóa, hết hạn, lỗi storage và nguồn. Kiểm tra public deployment được thực hiện riêng theo [runbook](OPERATIONS.md#triển-khai-và-xác-minh); fixture pass không chứng minh Turnstile hoặc LLM thật đã được xác minh.

## Handoff UI UX Redesign

| Luồng | Desktop sáng | Mobile sáng |
|---|---|---|
| Khởi đầu | `14:105` | `14:115` |
| Soạn câu hỏi từ gợi ý | `19:283` | `19:333` |
| Hội thoại | `14:106` | `14:116` |
| Đối chiếu nguồn | `14:107` | `14:117` |
| Thư viện | `14:108` | `14:118` |
| Đánh giá | `14:109` | `14:119` |
| Quá trình kiểm chứng | `14:110` | `14:120` |
| Dữ liệu và kết nối | `14:111` | `14:121` |
| Xóa lịch sử | `14:112` | `14:122` |
| Đang xử lý | `14:113` | `14:124` |
| Trạng thái gián đoạn | `14:114` | `14:125` |

Các frame tối nằm cùng trang, tên bắt đầu bằng `Dark`. Frame `14:147`–`14:150` thể hiện kiểm tra bố cục tại 320 và 1024 px. Foundations và component nằm ở `14:51`, với collection Theme có hai mode Light/Dark; màu, khoảng cách và bán kính được gắn biến. Nội dung trong mockup là minh họa bố cục, không phải kết quả pháp lý hay số liệu vận hành.

- Palette dùng các token `--surface`, `--sidebar`, `--tint`, `--ink`, `--muted`, `--border` và màu cảnh báo/lỗi. Body/composer 16 px, metadata 13 px, vùng chạm tối thiểu 44 px. UI dùng Be Vietnam Pro và icon Lucide.
- Gợi ý chỉ điền câu hỏi và focus ô nhập. Desktop dùng Enter gửi, Shift+Enter xuống dòng, giữ bảo vệ IME; thiết bị có con trỏ thô dùng Enter xuống dòng và nút gửi. Ô nhập tăng tới 160 px rồi cuộn nội bộ.
- Frontend đọc `/api/v1/status` để trình bày khả năng sinh đáp án riêng với `/readyz`. Không tự tạo thời gian chờ khi API thiếu metadata; không tự gửi lại POST chat.
- Thư viện phân biệt loading, fetch error, corpus rỗng và không có kết quả tìm kiếm; lọc loại nguồn diễn ra tại client. Lỗi storage hiện trên mọi trang; lỗi sao chép có thông báo riêng.
- Modal có focus trap, Escape và trả focus; vùng nguồn desktop không có focus trap. Trả focus dùng `preventScroll` để giữ vị trí đọc. Autoscroll chỉ hoạt động khi người dùng ở gần cuối.
- Xác nhận xóa lịch sử dùng dialog trong ứng dụng; không đổi session API hoặc quota. Theme vẫn hoạt động trong tab nếu localStorage không dùng được.

E2E cho redesign dùng fixture và xuất ảnh vào thư mục báo cáo mới, không ghi đè ảnh lịch sử. Cần phân biệt kiểm tra ARIA/bàn phím tự động với kiểm tra screen reader và bàn phím ảo trên thiết bị thật; kiểm tra public deployment, Groq và challenge (nếu đang bật) thực hiện riêng.

Thư viện gộp nguồn đã lập chỉ mục và bản gốc tham khảo, hỗ trợ tìm tiếng Việt không dấu. Bản gốc chưa lập chỉ mục có nhãn riêng và liên kết mở tài liệu chính thức. Phiên hết hạn giữ bản nháp, xóa token cũ và cho xác minh/gửi lại chủ động; storage bị chặn vẫn giữ phiên trong bộ nhớ tab. Status được cập nhật khi tab trở lại và sau cooldown provider. Báo cáo lệch fingerprint vẫn hiển thị đầy đủ số liệu; nhãn phiên bản nêu rõ cấu hình đã thay đổi.

Ảnh E2E dùng thư mục output của lần chạy Playwright; không ghi đè artifact lịch sử trong `reports/`.

Khi generation được cho phép trên snapshot, không hiển thị banner hoặc lời mở đầu tự động cảnh báo nguồn cũ. Với policy v2, đáp án pháp luật có thể kèm một câu ngắn ghi mốc `reviewed_at` và khuyến nghị kiểm tra văn bản gốc; đây là metadata nguồn, không phải banner cảnh báo. Metadata API, ngày kiểm tra nguồn và reports giữ trạng thái thực tế. Câu cảnh báo tự động ở đầu đáp án đã lưu trên thiết bị được bỏ khi hiển thị/sao chép; nội dung gốc trong IndexedDB không bị viết lại.

## Trang đánh giá (legacy)

Trang đánh giá và TracePanel đã bị gỡ khỏi UI từ commit `47ccff0`; `EvaluationPage.tsx`, `evaluation.ts`, `evaluationHighlights.ts` và các e2e spec liên quan chỉ còn là bề mặt legacy được giữ để bảo toàn checksum lịch sử. Không thêm lại dashboard công khai trong phạm vi MVP.
