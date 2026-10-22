# Các lần chạy live

## Attempt 1 — 22/10/2026

- Commit chạy: `2667a1a0fa06e6a1be87e9724628d54c3eb16fc9`.
- Kết quả: **không có file kết quả**; runner dừng sau ca pháp luật đầu tiên vì lỗi harness `RuntimeError: Event loop is closed`.
- Ledger: `attempt-1-budget-ledger.json`.
  - 1 request đã xác nhận, dùng 2.325 token thực tế.
  - 1 request ở trạng thái `reserved` (3.000 token đặt trước), không có response được xác nhận.
  - Tổng đặt trước tại thời điểm dừng: 6.000 token.
- Nguyên nhân: runner cũ dùng nhiều `asyncio.run` riêng cho từng ca nhưng dùng chung `httpx.AsyncClient`; connection pool gắn với event loop đã đóng.
- Không có ca nào được tính là hoàn thành. Không retry trong cùng attempt. File ledger được giữ nguyên byte để đối soát.
- Bản sửa dùng một event loop cho cả 5 ca và ghi lỗi harness thành `ERROR` thay vì làm mất kết quả; lần chạy thay thế cần ngân sách được duyệt riêng.
