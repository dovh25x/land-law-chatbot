# Ghi chú thuyết trình — 12 slide

## 1. Hanoi Land Law Assistant

Giới thiệu mục tiêu hỗ trợ đọc nguồn; không bảo đảm quyền lợi cá nhân. Thông tin hành chính để trống theo yêu cầu. Ngày evidence: 21/10/2026; đối chiếu delivery-status.json cho cập nhật phát hành. Bản bàn giao hiện tại bật SOURCE_LOOKUP_ONLY, tắt GENERATION_ENABLED. Không trình như một chatbot generative đã đạt quality acceptance.

Evidence: PRD · Báo cáo chương 1–2

## 2. Tìm được văn bản chưa đủ để kết luận

Ví dụ câu hỏi giả lập từ bộ acceptance; không dùng hồ sơ thật. Giải thích nhu cầu mở nguồn và hỏi lại. Không khẳng định dự án đã chứng minh cải thiện tiếp cận pháp luật qua nghiên cứu người dùng.

Evidence: PRD · Acceptance cases Phase 2C

## 3. Ba nhóm nghiệp vụ. Một phạm vi công bố.

Các cases có giả định cố định và phạm vi nguồn cụ thể; có nguồn không đồng nghĩa mỗi hồ sơ thật đều đủ điều kiện. Ngoài phạm vi: GIS/thửa đất, upload hồ sơ, tư vấn quyền lợi, đồng bộ tài khoản. Không nói bao phủ toàn Hà Nội.

Evidence: LEGAL_REVIEW.md · acceptance-cases-final.json

## 4. RAG giữ nguyên; demo chỉ tra cứu nguồn

Tái sử dụng sơ đồ repository đúng quy trình diagram-design; không vẽ sơ đồ mới. React/Vite qua signed Cloudflare ingress tới Render/PostgreSQL; Groq inference. Giữ LangGraph/Groq để tận dụng code đã tích hợp và giảm rủi ro chuyển đổi; không có benchmark chứng minh tốt hơn LlamaIndex/ChatGPT API. Source SVG/HTML trong docs/diagrams. Pipeline RAG được giữ trong code. Mode demo hiện tại không gọi model; SQLite source-only dba69995…, PG API local đã kiểm 8ee1cd63…. Không gán retrieval 1697 sang source-only.

Evidence: docs/diagrams/architecture.svg · ADR

## 5. Checksum bảo toàn phiên bản. Review quyết định phạm vi.

Review ngày 21/10 không tự gia hạn tới 23/10. HTTP 200 hoặc nội dung trùng snapshot không chứng minh hiệu lực. Corpus 1afca764aa6692e0; bundle/policy hashes trong manifest. Chỉ phạm vi Điều 95/98, 108, 111 và quy định phụ thuộc đã review cho từng case.

Evidence: Phase 2C legal review · source policy · receipts

## 6. Nguồn tìm thấy phải còn trong context thực gửi model.

C02 context 3/3 đơn vị, 5070 ký tự; C03 7/7, 6981/7000 ký tự. Citation integrity chỉ chứng minh nguồn đúng snapshot; semantic Citation Accuracy phải kiểm nội dung hỗ trợ kết luận. Guard hữu hạn vẫn có false positive, không hardcode S06 hoặc nới verifier.

Evidence: Phase 2D / Phase 3B synthesis capture

## 7. Đọc nguồn dễ hơn. Giới hạn phải nhìn thấy.

Dữ liệu vẫn được gửi provider khi inference, không nói mọi dữ liệu ở lại thiết bị. Không nhập PII. Unit/Playwright mocks không chứng minh cấu hình Turnstile/ingress production. Một repair nằm trong cùng attempt; không replay POST để che lỗi. Turnstile và flow chat là tính năng của pipeline giữ trong source, không tuyên bố đã public E2E trong source-only mode.

Evidence: FRONTEND.md · API.md · security/runtime tests

## 8. Đo từng lớp. Không thay tên bằng chứng.

19 queries có gold hợp lệ được dùng Recall: 10 smoke, 3 supplemental, 6 natural. S06 không chạy lại theo chỉ dẫn; 12 ca không có positive gold. Gold-bearing không tự là answerable. Refusal ca answerable không được chấm đúng. RAGAS chưa chạy; custom historical faithfulness không đổi nhãn thành RAGAS.

Evidence: EVALUATION.md · locked suites · retrieval receipt

## 9. Retrieval tốt ở mẫu nhỏ. Chưa đo accuracy đáp án.

Recall thuộc fingerprint RAG 1697…: macro trung bình trên 19 câu; 18 câu đạt 1 và một câu đạt 0,5; micro 20/21. Không phải legal-answer accuracy, không phải metric của source-only cuối. Code ec5 có 529 backend PASS trên CI Python 3.12 và local Python 3.14; 16 frontend unit/build/audit, 110 Playwright fixture PASS. Không cộng các run hoặc baseline 516/100 vào mẫu cuối. Image cuối d1ff… có peak RSS 381,796875 MiB trong offline fixture probe; số 381,70703125 MiB candidate đầu và 382,6640625 MiB Phase 4 thuộc image khác. PostgreSQL source API/role và rollback restore có receipts riêng; không phải PG Recall hoặc public load test.

Evidence: Recall: Phase 3B 1697… · Software/image/PG: release-final-20261021

## 10. Giữ cả các lượt chưa thành công.

C01 có 4.829 tokens provider xác nhận; unknown upper bounds không phải usage thực. 34,858 giây là attempt chưa hoàn tất, không phải latency đáp án thành công. S06 thuộc fingerprint 2dab…, C01 37d…, candidate offline 1697…. C02 trong allocation mới 25.000 tokens trên 1697…: 1 HTTP 400 json_validate_failed do output truncate; 6.951 ms; 0 confirmed không nghĩa actual bằng 0; unknown upper bound 19.788, remaining 5.212. Request tiếp theo bị preflight chặn; không phát hành answer/citation và không chạy lại. C02/C03 Phase 3A vẫn NOT RUN.

Evidence: S06 technical review · Phase 3A C01 · accounting ledger

## 11. Trình bày điều đã đo. Dán nhãn phần chưa đo.

Demo 5 phút theo DEMO_GUIDE.md. Public E2E chỉ gọi PASS khi xác minh đúng SHA/corpus/fingerprint và browser live; Turnstile phải qua tương tác người dùng bình thường, không bypass. Nếu chỉ replay artifact hoặc UI local, nói rõ đây không phải cloud model. Không dùng draft C01/S06 làm legal answer. Release owner cập nhật URL và trạng thái riêng; fallback chỉ được gọi đã triển khai khi có bằng chứng. Local API source lookup PASS, 0 provider generate calls. Ngày lịch sử 02/08/2024 có 25 passages; ngày 21/10/2026 có 43; ngày 22–23 chỉ 1 header. Không gọi chat 503 là semantic refusal pass. C04/C05 chỉ xem fixture cũ nếu cần giải thích RAG. Final ec5 public run03 PASS_SOURCE_ONLY_PUBLIC_BROWSER, nguồn43/1/25 đúngchecksum; linkQD40HTTP 200đúngtitle; reload/historywarningclear/mobilekhôngoverflow. KhônghumanTurnstile/chat/followuphayphysicalmobile. HaiFAILtrướcgiữnguyên.

Evidence: DEMO_GUIDE.md · source/capture receipts

## 12. MVP nhỏ, có nguồn, khai báo đúng giới hạn.

Bản bàn giao source lookup đã deploy code ec5, CI PASS 529/16/110 và public browser desktop/mobile emulation PASS trong phạm vi nguồn. Không có model/session requests. Chat, follow-up và human Turnstile không khả dụng/chưa kiểm. Tag v0.1.0-academic-20261021 dự kiến trỏ docs/evidence commit sau code; identity deploy giữ ec5. Không cam kết hiệu lực mọi văn bản hoặc accuracy 100%. Public source-only PASS không biến model FAIL/INCOMPLETE thành PASS. Hướng sau học phần: review độc lập/holdout, false abstention, API reliability và usability; chưa triển khai hoặc đo mới.

Evidence: delivery-status.json · release manifest · LIMITATIONS.md