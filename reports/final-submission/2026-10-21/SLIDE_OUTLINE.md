# Dàn ý 12 slide — khoảng 10 phút

Đây là nội dung biên soạn, **chưa phải file slide đã thiết kế/xuất PDF**. Thông tin tên/MSSV/học phần/giảng viên để trống. Không dùng transcript giả hoặc ảnh model pass không tồn tại. Đường dẫn hình và số liệu dẫn về [evidence index](EVIDENCE_INDEX.md).

| Slide | Thời lượng | Nội dung trên slide | Hình/evidence và lời nói chính |
|---|---:|---|---|
| 1. Đề tài và mục tiêu | 30 s | Hanoi Land Law Assistant; Vành đai 4 Hà Nội; tra cứu có nguồn | Bìa thông tin trống. “Mục tiêu là giúp đọc nguồn, không quyết định quyền lợi.” |
| 2. Bài toán người dùng | 45 s | Văn bản nhiều cấp; mốc thời gian; dữ kiện hồ sơ còn thiếu | Một câu hỏi giả lập từ case khóa, không hồ sơ thật. Phân biệt tìm nguồn và tư vấn áp dụng cá nhân. |
| 3. Phạm vi MVP | 40 s | Bồi thường/hỗ trợ/tái định cư; không GIS, tính tiền, hồ sơ | Trích PRD và ba case C01–C03 cùng giả định. Không gọi toàn Hà Nội là scope đã bao phủ. |
| 4. Kiến trúc thực tế | 60 s | React/Vite → Cloudflare → Render/FastAPI/LangGraph → PG; Groq và E5 | Dùng [architecture.svg](../../../docs/diagrams/architecture.svg), giữ attribution/source HTML theo repository. Nêu local SQLite khác PG. |
| 5. Vì sao stack này | 35 s | Giữ hệ thống đang có; graph hữu hạn; dịch vụ/model đã cấu hình; Free hosting | Giải thích khác đề xuất LlamaIndex/ChatGPT API; chưa benchmark framework, không khẳng định hơn kém. |
| 6. Corpus và hiệu lực | 60 s | Provenance/checksum; scoped review; không HTTP200=fresh | 60 records/7.396 chunks là quy mô snapshot, không fresh coverage. Ngày review 21/10, ngày demo cần kiểm riêng. |
| 7. RAG và chặn claim thiếu căn cứ | 60 s | Hybrid retrieval; context ledger; claim verification; bounded repair | Dùng diagram sẵn có nếu đúng pipeline, hoặc bảng bước; không vẽ Mermaid thay quy trình. F01 fail-closed; khoản dẫn chiếu/OR-AND không giải quyết bằng hardcode đáp án. |
| 8. Giao diện, privacy, vận hành | 40 s | Source panel; loading/errors; browser history 7 ngày; metadata server | Có UI/Playwright fixtures; public ingress/Turnstile mới chưa xác minh. Không gọi mock browser là live cloud demo. |
| 9. Thiết kế đánh giá | 55 s | 20+4+8 khóa; software/retrieval/context/model tách riêng | Giải thích 19 câu có gold, 13 exclusions có ghi lý do; gold không tự là answerable label. |
| 10. Kết quả có evidence | 65 s | 516 backend;14 frontend;100 local Playwright;Recall@5 97,37% macro,20/21 micro 95,24% | Dòng lớn “SQLite retrieval ≠ answer accuracy”. Context C02 3/3, C03 7/7; model metrics final NOT MEASURED. Docker/PG cập nhật theo receipt Phase 4, không tự thêm deployment PASS. |
| 11. Failure analysis và demo | 80 s | S06 FAIL; C01 INCOMPLETE; C02/C03 NOT RUN Phase 3A; 429/400/budget | Show receipt thật và source/retrieval evidence theo [demo script](DEMO_SCRIPT.md). Không lấy draft chưa verify làm answer. |
| 12. Kết luận và việc còn thiếu | 30 s | Đã xây phần mềm/nguồn/guards; chưa đủ evidence cloud/model; giới hạn | Nêu deploy NOT READY, các bước tối thiểu và hướng nghiên cứu. Không hứa accuracy/grade hoặc deadline cloud chưa kiểm. |

Tổng khoảng 10 phút; nếu có 3–5 phút demo riêng, rút slide 11 xuống 30 giây và theo demo script. Trước xuất slide, đối chiếu các số với manifest/checklist, không dùng screenshots của runtime cũ làm ảnh candidate mới mà thiếu nhãn.

## Câu hỏi dự kiến của hội đồng

- **“97,37% chính xác không?”** Là tìm gold chunks trong top 5, macro trên 19 câu SQLite; độ đúng đáp án model cuối chưa đo.
- **“Vì sao không LlamaIndex/ChatGPT?”** Giữ kiến trúc thực thi hữu hạn đã triển khai và giảm rủi ro chuyển đổi một người; chưa có thí nghiệm so sánh để kết luận stack tốt hơn.
- **“Có chắc văn bản mới nhất?”** Chỉ các đoạn/ngày có review và receipt checksum; không toàn corpus, không tự suy ngày 23/10 từ 21/10.
- **“Demo model trả lời được không?”** Candidate cuối chưa có model-answer pass. Trình diễn phần evidence đã xác nhận và công bố hạn chế; không tạo transcript thay thế.
- **“Vì sao từ chối dù có nguồn?”** Có thể thiếu điều kiện/synthesis/citation hoặc guard; cần đo false abstention, không mặc định refusal là đúng.
- **“Phát hành chưa?”** Candidate đang freeze để review; chưa commit/deploy mới và chưa public E2E đúng tuple.
