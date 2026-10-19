# Ưu tiên chỉ số nổi bật trên dashboard — 2026-10-19

Theo yêu cầu chủ dự án, đưa các số liệu tốt nhất đã ghi nhận lên đầu trang Đánh giá hệ thống. Đây là thay đổi thứ tự/trình bày, không chạy lại benchmark hoặc sửa kết quả gốc.

## Cách chọn

- Tỷ lệ đạt bộ chính: chọn tỷ lệ cao nhất trong suite đã thực hiện đủ, rà soát đủ, counts khớp mẫu số. Các lượt còn dở/chưa rà soát không được dùng làm thành tích.
- Recall@8: chọn giá trị cao nhất trong phép đo k=8 có mẫu. Khi bằng điểm ưu tiên mẫu lớn hơn, cùng corpus rồi thời điểm mới hơn.
- Faithfulness: chọn điểm cao nhất có ca và mệnh đề đã chấm; giữ coverage đầy đủ. Điểm null/không có mẫu không được đổi thành số.
- Tỷ lệ bộ chính và faithfulness đồng hạng ưu tiên mẫu lớn hơn rồi lần đo mới hơn. Không trộn các chỉ số thành một điểm chung.

Giao diện hiện đưa lên đầu 95% bộ chính (19/20 ca của cấu hình SQLite lịch sử 817e3825…), 100% Recall@8 (3 ca có gold của bộ bổ sung trên PostgreSQL), 92,3% faithfulness (6/8 ca có điểm, 13 mệnh đề, cấu hình c4f0c661…). Mỗi thẻ hiện mẫu, thời gian, backend, cấu hình, quan hệ với corpus hiện tại và link artifact ghim revision. Không gọi đây là độ chính xác tổng thể hoặc số đo của deployment hiện tại.

Bộ chi tiết vẫn mặc định là bộ đầy đủ gần nhất của corpus đang phục vụ, với 22/32 đạt, 3 một phần và 7 chưa đạt. Không đổi default_run_id, archive, JSON download, verdict, fingerprint hoặc mẫu số. Nút xem toàn bộ kết quả dẫn thẳng xuống phần chi tiết; đủ 13 nhóm run/63 artifact và các ca chưa đạt vẫn truy cập được.

## Kiểm chứng

Source frontend: `35d3d5b6361715e204a07dba0eed4ec80c502032`.

- Backend: 259 passed; không thay source backend trong patch.
- Frontend unit: 10 passed, gồm không lấy lượt chưa đầy đủ/chưa rà soát, không suy điểm từ mẫu trống, giữ provenance/coverage và không mutate archive/default selection.
- Frontend build và secret scan đạt.
- E2E: 88 passed trên desktop/mobile. Regression mới kiểm tra ba con số nổi bật, nhãn lịch sử, phạm vi 3 ca/6-of-8, thứ tự trước bảng chi tiết, default selection không đổi, giữ 7 ca chưa đạt và nút điều hướng.
- Xem trực quan ảnh desktop sáng; ảnh local-ui giữ các bản desktop/mobile sáng/tối của bộ E2E đầy đủ.

Chỉ triển khai frontend vì source backend, corpus và dữ liệu đánh giá không đổi. Backend tiếp tục phục vụ source đã kiểm thử trước đó; fingerprint và SHA-256 archive được đối chiếu trong runtime-identity.json. Không gọi LLM thật, không đổi model/embedding/hosting, không sửa artifact lịch sử hoặc thêm banner snapshot vào chat.

## Production đã xác minh

- Cloudflare production `5ffd3fb8-0b3f-4d22-99c3-a5e17727e483` đã success đúng SHA frontend `35d3d5b6361715e204a07dba0eed4ec80c502032`. Backend Render vẫn live source `371e8c2461f457d36f833320eb2361bb6a10c8eb`, được đối chiếu bằng API metadata; không redeploy backend cho thay đổi giao diện này.
- [CI 39215003273](https://github.com/dovh25x/land-law-chatbot/actions/runs/39215003273) success cả backend, frontend và Docker memory 512 MiB.
- `live-ui.json` xác nhận 1440/390/320 px đạt: 95%/100%/92,3% hiển thị trước bảng chi tiết, đúng mẫu và nhãn lịch sử, có link source; default_run_id vẫn nguyên, bộ chi tiết vẫn 22/32 đạt và 7 chưa đạt; bộ lọc truy cập đủ 7 ca, đủ 13 run và 63 source.
- Ảnh live-*.png giữ giao diện thực. Đã xem trực quan desktop sáng local và mobile production. Không gọi chat/Groq trong phép kiểm tra này.
