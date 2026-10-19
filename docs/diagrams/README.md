# Nguồn và quy trình xuất diagram

Các sơ đồ kỹ thuật dùng [diagram-design](https://github.com/cathrynlavery/diagram-design/tree/550fd66edff058bc73056c3416b76d69cfe865ba), ghim commit `550fd66edff058bc73056c3416b76d69cfe865ba`, giấy phép MIT, theo style mặc định. Sơ đồ kiến trúc độc lập với thiết kế UI trên Figma.

## Danh mục

| Sơ đồ | Nguồn có thể chỉnh sửa | Asset nhúng Markdown |
|---|---|---|
| Kiến trúc hệ thống | [architecture.html](architecture.html) | [architecture.svg](architecture.svg) |
| Trình tự chat | [chat-sequence.html](chat-sequence.html) | [chat-sequence.svg](chat-sequence.svg) |
| Vòng đời corpus | [corpus-lifecycle.html](corpus-lifecycle.html) | [corpus-lifecycle.svg](corpus-lifecycle.svg) |
| Agent flow | [agent-flow.html](agent-flow.html) | [agent-flow.svg](agent-flow.svg) |
| Cổng phát hành đáp án | [agent-publication-gate.html](agent-publication-gate.html) | [agent-publication-gate.svg](agent-publication-gate.svg) |
| Triển khai và khôi phục | [deploy-recovery.html](deploy-recovery.html) | [deploy-recovery.svg](deploy-recovery.svg) |

Tất cả sơ đồ của hệ thống dùng `diagram-design`: HTML là source, SVG được xuất bằng helper và nhúng trong Markdown. Không dùng Mermaid hoặc công cụ khác thay thế. [Kiến trúc](../ARCHITECTURE.md#agent-flow) và [phân tích agent](../AGENT_FLOW.md) cùng dùng asset agent flow; sơ đồ trình tự chat được tái sử dụng để tránh nhiều bản lệch nhau.

Agent flow dùng preset `doc-wide` 1280 × 720, mức chi tiết cân bằng cho người đọc kỹ thuật. START/END được gộp vào node đầu/cuối; cổng phát hành gộp verdict và phạm vi vào một quyết định; chú thích phân biệt freshness mặc định với snapshot được chủ động cho phép. Các điều kiện chi tiết giữ trong [phân tích agent](../AGENT_FLOW.md).

## Quy trình cập nhật

1. Sửa file HTML tương ứng; đây là source của sơ đồ.
2. Đọc skill `skills/diagram-design/SKILL.md` và reference của loại sơ đồ tương ứng tại commit đã ghim. Dùng `skills/diagram-design/scripts/export_svg.py` từ commit đã ghim để xuất lại SVG. Xem `--help` của helper tại đúng revision trước khi chạy.
3. Chạy self-check và kiểm tra geometry từ cùng bộ công cụ; xem trực quan bản xuất để phát hiện chữ tràn, clipping và đường nối sai.
4. Commit cả HTML và SVG, cập nhật liên kết nếu đổi tên file.

Giữ title/description phục vụ accessibility, hierarchy nhất quán và đường nối trực giao. Không dùng screenshot làm source, không sửa riêng SVG rồi để HTML lệch phiên bản. Tài liệu Markdown nhúng SVG; HTML chỉ dùng để biên tập và kiểm tra.
