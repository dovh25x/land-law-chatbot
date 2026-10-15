# Hanoi Land Law Assistant
## Báo cáo đồ án liên ngành — nguyên mẫu học thuật

**Sinh viên/nhóm, lớp, giảng viên:** điền thông tin trước khi nộp.

## 1. Bài toán và mục tiêu

Văn bản pháp luật phân tán, có thay đổi theo thời điểm và thường khó đọc với người không chuyên. Đồ án xây dựng web chatbot tiếng Việt hỗ trợ tìm căn cứ về bồi thường, hỗ trợ và tái định cư ở Hà Nội. Vành đai 4 là tình huống minh họa. Mục tiêu là minh họa một hệ thống AI có truy xuất và nguồn dẫn, không xác định quyền lợi pháp lý của từng hộ.

## 2. Đóng góp liên ngành

| Lĩnh vực | Công việc |
|---|---|
| Kỹ thuật dữ liệu | Thu thập nguồn chính thức, parse HTML/PDF, chia đoạn theo cấu trúc, metadata và phiên bản |
| Trí tuệ nhân tạo | Embedding E5, hybrid retrieval, LangGraph, tổng hợp có chứng cứ và kiểm tra trích dẫn |
| Kỹ thuật phần mềm | React/TypeScript, FastAPI, phiên hội thoại, SSE, Docker, kiểm thử và triển khai |
| Kiến thức miền | Phân biệt quy định chung, hồ sơ dự án, thời điểm áp dụng và dữ kiện cá nhân còn thiếu |

## 3. Kiến trúc

```mermaid
flowchart LR
    D[Nguồn chính thức] --> P[Parse và chia đoạn ngoại tuyến]
    P --> E[E5 embedding trên Colab]
    E --> DB[(Supabase PostgreSQL pgvector)]
    W[React web] --> API[FastAPI SSE]
    API --> G[LangGraph và công cụ chỉ đọc]
    G --> DB
    G --> N[Groq GPT-OSS 20B]
    N --> V[Kiểm tra nguồn và trích dẫn]
    V --> W
```

Backend và frontend chạy riêng trên Render và Cloudflare Pages. Supabase lưu corpus và hội thoại. E5 xử lý truy vấn trên CPU backend; không chạy mô hình sinh hoặc OCR trên Render. Không sử dụng công nghệ embedding khác trong cùng index.

## 4. Dữ liệu và retrieval

Corpus snapshot đang sử dụng có 69 tài liệu và 7.610 vector 384 chiều; danh mục nguồn nằm tại `data/sources.json`. Văn bản được lưu nguồn công bố, checksum, ngày kiểm tra và locator điều/khoản/trang. OCR và dữ liệu chưa đạt kiểm tra không được dùng để bù số lượng. Tin tiến độ dự án chỉ bổ sung bối cảnh.

Hybrid retrieval kết hợp tìm từ khóa PostgreSQL và vector bằng Reciprocal Rank Fusion. Kết quả truy xuất là ứng viên; không tự chứng minh điều khoản áp dụng cho hồ sơ cá nhân. Nguồn dẫn cho phép mở đoạn và văn bản gốc.

## 5. Agent và giao diện

Workflow xác định vấn đề, gọi công cụ truy xuất/mở điều khoản/quan hệ văn bản, tổng hợp rồi kiểm tra trước khi phát đáp án qua SSE. Có giới hạn thực thi để tránh vòng lặp. Trace hiển thị sự kiện và công cụ thực tế, không hiển thị suy nghĩ nội bộ.

Người dùng nhập câu hỏi, chọn ngày/dự án nếu cần, đọc đáp án và mở nguồn/trace. Hệ thống có thể hỏi lại hoặc trả lời có giới hạn. Baseline được giữ để minh họa nhưng không giả định agentic luôn tốt hơn.

## 6. Phương pháp đánh giá

Dùng lại 20 câu smoke có rubric và nguồn tham chiếu tại `data/evaluation/smoke.jsonl`. Chạy 20 ca agentic qua CLI quản trị trên mã nguồn bản chốt, gọi Groq thật và corpus Supabase. Lưu câu trả lời, model, corpus, fingerprint, độ trễ và đối chiếu ID/đoạn nguồn. CLI không chịu giới hạn chống lạm dụng của website nhưng tuân thủ quota provider, có checkpoint và giữ lịch sử lần thử. S14 dùng lịch sử cố định của bộ kiểm tra; hội thoại tự nhiên qua HTTPS/browser được kiểm chứng riêng. Không ghép độ trễ CLI thành SLA HTTP.

Kết quả mới được lưu riêng tại `reports/submission/evaluation.json`; bảng dễ đọc tại `reports/submission/results.md`. Kiểm tra máy chỉ xác nhận giao thức và nguồn tồn tại; chấm nội dung cần đọc câu trả lời và đối chiếu rubric. Những câu chưa rà soát phải ghi `awaiting_review`, không tính là đạt. Không lấy số liệu cũ, CLI hoặc model khác để thay thế.

## 7. Kết quả và bằng chứng

Đã chạy và rà soát đủ **20/20 ca agentic** với Groq `openai/gpt-oss-20b`, release `corpus-de584c31fc95f9a2`, fingerprint `2952b6bbdef6c0e4c3099762c4cec4cd1911ee25f6c3d5b01ec3a8e8216fe240`. Kết quả theo rubric kỹ thuật và đoạn nguồn: **17 pass, 3 partial, 0 fail**. Tất cả ID/đoạn trích dẫn xuất hiện khớp corpus; điều này không bảo đảm mọi mệnh đề được hỗ trợ.

- S04 trả đúng tiếp tục phương án, còn thiếu ý chi trả chậm trong rubric đầy đủ.
- S11 không khẳng định quyền lợi cá nhân nhưng chưa giải thích riêng nguồn tin quy hoạch được hỏi.
- S16 không xác nhận số tiền/văn bản giả, nhưng hướng dẫn kiểm tra còn chung.
- S06 của bản cuối trả lời có nguồn về các điều kiện thay thế và giữ điều kiện thuộc khoản 1, được chấm pass. Run trước trên fingerprint khác từng liệt kê đối tượng chưa được citation hỗ trợ đầy đủ; khác biệt này nhắc rằng một run tốt không bảo đảm mọi lần sinh đúng.

Có 21 lần thực thi cho 20 ca ở fingerprint cuối: S01 từng timeout, sau đó thử lại thành công. S06/S16 có retry do TPM trong ngân sách mỗi lượt. Giữ cả lần thử lỗi; bảng chính ghi lần thực thi cuối và không giấu việc thử lại. Không dùng LLM judge. Không suy tỷ lệ toàn miền hoặc chứng nhận nghiệm thu pháp lý từ bộ 20 câu có chọn lọc. Phiên bản mã nguồn không chứa thay đổi `agent.py` đang dở trong workspace.

Bản chính sách demo đã qua 230 kiểm thử backend/công cụ; hai regression bổ sung xác nhận Groq không sử dụng khóa NVIDIA, kể cả khi thiếu khóa Groq. Frontend đạt 2 unit tests và 22 E2E desktop/mobile. CI, triển khai, HTTPS và video có receipt riêng trong `reports/submission/`. Baseline và agentic đã được kiểm chứng sinh câu trả lời Groq thật qua HTTPS, có nguồn/trace, lưu hội thoại và cách ly phiên; xem `reports/live-demo.json`. Gói corpus-only đã restore thành công vào SQLite riêng, đủ 69 tài liệu/7.610 vector và không có phiên cá nhân.

Các receipt trước đây ở `reports/live-demo.json`, `reports/live-ui.json` và `reports/postgres-restore.json` là bằng chứng lịch sử, không tự động là kết quả của mã nguồn hiện tại.

## 8. Hạn chế

- Chưa được thẩm định pháp lý độc lập; dữ liệu là snapshot, có nguồn và quan hệ còn thiếu.
- Retrieval và giải tham chiếu có thể bỏ sót; một số câu hỏi bị trả lời giới hạn dù có căn cứ trong corpus.
- Nguồn đúng không tự bảo đảm mọi kết luận trong đáp án đúng.
- Hosting miễn phí có cold start; provider có thể timeout/quota. Không cam kết SLA.
- Không tính tiền bồi thường, xác định quy hoạch từng thửa hay xử lý hồ sơ cá nhân nhạy cảm.
- 20 ca có chọn lọc không đại diện mọi câu hỏi thực tế; không tuyên bố cải thiện so với baseline nếu chưa đo cùng cấu hình.

## 9. Hướng phát triển

Chỉ sau học phần: mở rộng đánh giá, thẩm định miền độc lập, cải thiện retrieval và giải tham chiếu, cập nhật nguồn có kiểm duyệt. Đây không phải điều kiện hoàn thành bản nộp.

## 10. Tài liệu tham khảo và tái lập

Nguồn pháp lý: `data/sources.json`, trang nguồn trong ứng dụng và metadata corpus. Công nghệ: FastAPI, LangGraph, PostgreSQL/pgvector, multilingual-e5-small, Groq hosted GPT-OSS 20B, React/Vite. Cài đặt theo README và phiên bản khóa trong repository. Không đưa khóa API hoặc token phiên vào báo cáo.
