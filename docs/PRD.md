# PRD — Hanoi Land Law Assistant

## Mục tiêu
Nguyên mẫu học thuật CSE703014: xử lý văn bản pháp luật, Agentic RAG và web full-stack. Người dùng là sinh viên, giảng viên và người tra cứu tình huống giả định. Chưa được thẩm định pháp lý độc lập.

## Yêu cầu
- Chat tiếng Việt, hỏi tiếp, trích dẫn mở được và agent trace chỉ hiển thị sự kiện thực thi.
- Pháp luật chung về bồi thường, hỗ trợ, tái định cư Hà Nội; dự án duy nhất được hỗ trợ thao tác là Vành đai 4.
- Corpus giữ 69 tài liệu/7.610 vector E5; nguồn dự án khác vẫn trong thư viện để tham khảo. Câu hỏi riêng về Sông Hồng/Olympic phải thông báo ngoài phạm vi.
- Chỉ Agentic RAG; bỏ baseline vì không có bộ kết quả so sánh đầy đủ cùng cấu hình.
- Groq GPT-OSS 120B ưu tiên; chỉ chốt 20B nếu quyền/quota ngăn hoàn thành. Không đổi model tự động, đánh giá phải khớp model bàn giao.
- Composer một dòng sau khi có hội thoại, cao 56–64 px; tự giãn tối đa 120 px; không phủ nội dung.

## Công nghệ
React/Vite/TypeScript, FastAPI, LangGraph, Groq, E5 ONNX Q8 384 chiều, PostgreSQL/pgvector (cloud), SQLite (local), Cloudflare Pages, Render Free, Supabase. Không embedding lại hoặc nâng gói trả phí.

## Không thuộc phạm vi
Tư vấn hồ sơ cá nhân, tính tiền, GIS thửa đất, chứng nhận pháp lý, cập nhật nguồn theo lịch, benchmark 120/80 câu, SLA production, nhiều provider, báo cáo học phần/slide/video.

## Bảo vệ và giới hạn
Secret ở backend; token phiên được hash; không truy cập chéo phiên; công cụ chỉ đọc; kiểm tra nguồn và JSON; 6 LLM/12 công cụ/2 vòng truy xuất/90 giây mỗi lượt; chống lạm dụng theo phiên/IP. Lỗi/quota được thông báo rõ.

## Chuẩn đầu ra
Tài liệu học phần: https://drive.google.com/file/d/1jHi1UL_6FNm-6X_Hi30elZmyUFPvCXKc/view (đề cương 2022–2023, không có trọng số điểm). LO.01: PRD và thiết kế; LO.02: README/tài liệu, trình bày trực tiếp do sinh viên thực hiện; LO.03: nguồn, đạo đức, giới hạn; LO.04: đóng góp nhóm thực tế nếu làm nhóm; LO.05: công nghệ an toàn. Không tạo bằng chứng đóng góp giả.

## Hoàn thành
URL và local hoạt động; chat/hỏi tiếp/nguồn/trace đạt kiểm tra; build/tests/secret scan đạt; 20 câu được khóa trước chạy và rà soát trên đúng model/corpus/runtime; công khai lỗi; docs thống nhất; mã cần thiết commit/push; không tuyên bố nghiệm thu pháp lý.
