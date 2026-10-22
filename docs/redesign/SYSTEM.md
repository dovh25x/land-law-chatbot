# Thiết kế kỹ thuật đích

> **Design record — historical.** Tài liệu này được viết trước khi bounded Agentic RAG lên production; các đoạn nói về planner/verifier/repair, budget 6/12/2/1 hoặc schema-2 có thể không còn đúng. Runtime hiện hành: [AGENTIC_RAG.md](../AGENTIC_RAG.md) và [ARCHITECTURE.md](../ARCHITECTURE.md).


Giữ một graph và toàn bộ topology hạ tầng hiện tại. Thay đổi nằm trong cách biểu diễn nhu cầu, chọn nguồn, tạo/kiểm chứng hướng dẫn và trình bày kết quả. Mọi trường hoặc module đề xuất dưới đây **chưa tồn tại trong runtime**, trừ phần được ghi là tái sử dụng.

## Thành phần giữ nguyên

![Hạ tầng tái sử dụng](../diagrams/architecture.svg)

Sơ đồ này mô tả hạ tầng đang có, được tái sử dụng cho v2; không mô tả các contract mới. React/Vite qua Cloudflare signed ingress tới FastAPI trên Render, PostgreSQL/pgvector; E5 ONNX Q8 384 chiều chạy tại backend, generation dùng Groq GPT-OSS 120B. SQLite chỉ phục vụ local. Ingest/OCR và xuất bản corpus tiếp tục ngoại tuyến. Không thêm service, endpoint proxy tùy ý, remote tool hoặc pipeline trả lời khác.

Giữ trần 6 LLM requests gồm retry, 12 tools, 2 retrieval rounds, 1 repair, deadline 90 giây. Giữ quota public/operator, Turnstile, lease/idempotency, không replay đáp án và lịch sử IndexedDB 7 ngày. Không có bước “viết lại cho dễ hiểu” bằng LLM sau verify.

## Luồng trong graph hiện có

| Node | Trách nhiệm mới trong node | Bất biến |
|---|---|---|
| `plan` | Trích nhu cầu và dữ kiện có provenance; chọn câu hỏi làm rõ có ích; nhận diện câu hỏi quy định chung dù dùng ngôi “tôi” | Không suy từ cách nói thành điều kiện pháp lý; định tuyến không được xác nhận quyền lợi |
| `tools` | Truy xuất câu gốc và từ tương đương đời thường; chọn nguồn theo vai trò, địa bàn, thời điểm; mở phụ thuộc | Vẫn tools chỉ đọc; mọi truy xuất mới tính vào trần hiện có |
| `synthesize` | Tạo câu trả lời dễ hiểu và hành động dưới dạng các claim có nguồn; đặt câu hỏi còn thiếu | Diễn giải, hướng dẫn nộp giấy, đầu mối và thời hạn đều vào draft trước verify |
| `verify` | Kiểm tra thêm vai trò nguồn, điều kiện hành động, giấy bắt buộc/tùy chọn, cơ quan nhận/giải quyết, freshness | Không chỉ kiểm tra quote khớp; veto cấu trúc vẫn có hiệu lực |
| `repair` | Sửa đúng lỗi trong toàn bộ draft, gồm nội dung hành động và tham chiếu UI | Tối đa một lần; toàn draft được verify lại |
| `finish` | Chiếu nguyên văn claim đã duyệt vào các phần; thêm nhãn điều hướng cố định | Còn issues/needs_more_evidence hoặc thiếu claim được duyệt thì bỏ cả nhóm claim và citation |

Đường thường dự kiến 2 requests (synthesis + verify) khi routing đủ chắc; câu mơ hồ có thể thêm planner. Đây là thiết kế ngân sách, không phải số đo latency hoặc cam kết số calls. Nếu planner được gọi, trích nhu cầu trong cùng output Plan, không thêm một model riêng. Không fan-out các câu con thành nhiều agent.

## Trạng thái nhu cầu trong bộ nhớ

`CitizenNeed` đề xuất có `intent` (orientation, explain_document, prepare_documents, understand_benefit, find_contact, disagreement, explain_term), `stage`, `place`, `document_type`, `relevant_dates`, `known_facts`, `unknown_facts`. Mỗi fact gắn `origin=current_user|history_user`, lượt cung cấp và trạng thái `unconfirmed|confirmed_by_user`; không có nhãn “đã được pháp luật xác nhận” cho dữ kiện người dùng.

Tên gọi đời thường như “đền bù”, “sổ đỏ”, “giấy thu hồi” là gợi ý truy xuất. Giữ cả nguyên văn và cách chuẩn hóa; “giấy thu hồi” chưa đủ để gán là quyết định. Alias phải là từ tương đương truy vấn, không chứa câu trả lời, mức tiền hoặc điều kiện được suy ra. Trường pháp lý lấy từ nguồn, không từ tên topic.

Chỉ hỏi dữ kiện làm thay đổi nguồn hoặc hướng giải thích. Với yêu cầu bảo đảm quyền lợi riêng, chặn kết luận cá nhân nhưng có thể truy xuất phần quy định chung liên quan. Không tái sử dụng claim thuộc một draft hỗn hợp đã fail: phần giải thích chung phải được xác định từ trước, tạo và verify như một nhóm độc lập; nếu nhóm này fail thì bỏ toàn bộ. Không thêm fallback generation sau khi đã hết budget.

Người dùng sửa ngày/địa bàn thì dữ kiện mới thay thế giá trị cũ cho lượt đó; không viết đè câu trả lời cũ. Nếu lịch sử đã bị cắt theo giới hạn, hỏi lại và nêu rõ không còn đủ ngữ cảnh. Không tin `document_number`, `claims`, citation hay intent do client gửi là chứng cứ.

## Contract API đề xuất

Giữ endpoint `/api/v1/chat` và SSE `progress/result/failure`. Khi triển khai, tăng `api_version` từ contract hiện tại lên 3; đây không phải đổi URL. Client cũ đọc `content` như trước. Client mới chỉ dùng khối cấu trúc khi có `answer_schema_version=2`, qua validation chặt và feature flag; thiếu trường thì fallback `content`.

| Trường mới | Dữ liệu | Validation |
|---|---|---|
| Request `interaction` | Optional intent/stage lựa chọn bởi người dùng, enum và độ dài cố định | Không tự cấp quyền, không ghi đè `message` hoặc xem là dữ kiện đã xác minh; vẫn body 64 KiB |
| Result `answer_schema_version` | `2` | Chỉ phát khi server thực sự dựng theo schema mới |
| `answer_sections` | Nhóm `direct`, `explanation`, `actions`; mỗi nhóm chứa `claim_indexes` | Chỉ tham chiếu `verified_claims` của chính response; giữ nguyên text, không có prose pháp lý tự do |
| `clarification` | Một `question`, tối đa ba lựa chọn, `allow_unknown`, mã fact cần hỏi | Không yêu cầu định danh, không chứa hướng dẫn pháp lý chưa verify; lượt hỏi mới do người dùng chủ động |
| `source_context` | Ngày xem xét, ngày rà soát, vai trò và tình trạng đủ nguồn cho từng nhóm | Không lấy ngày request làm ngày nguồn đã được rà soát |
| `need_more_context` | Mã lý do thiếu stage/date/place/source | Không tự đổi thành “không có quyền” |

`verified_claims` vẫn là nguồn văn bản duy nhất cho UI có nội dung thực chất. Mỗi claim có ID/index ổn định trong response và citation IDs hiện có. Có thể bổ sung `kind=procedure|contact` vào enum hiện tại để verifier phân biệt nguồn thủ tục/danh bạ; `legal_rule`, `applicability`, `context` giữ nguyên. Cập nhật tất cả schema strict/provider, export/evaluation và các consumer trước khi bật trường mới.

Ví dụ khung, không phải response pháp lý thực:

```json
{
  "answer_schema_version": 2,
  "answer_sections": [
    {"kind": "direct", "claim_indexes": [0]},
    {"kind": "actions", "claim_indexes": [1]}
  ],
  "clarification": null
}
```

Ví dụ giả định hai claim đã được duyệt tồn tại trong response. Nếu claim 1 không được duyệt, không chỉ bỏ thẻ action: cả nhóm draft tuân theo cổng veto hiện có. Kiểm tra không có index mồ côi, không trùng text/nguồn khác lượt và `answered` luôn có claim. `content` do server render từ cùng claims/sections, không do frontend tóm tắt lần nữa.

`clarification_needed` có thể đi cùng phần giải thích chung đã verify và một câu hỏi. `insufficient_evidence` phân biệt thiếu nguồn với thiếu thông tin người dùng; phần hướng dẫn giao diện cố định chỉ giúp mở tài liệu/nhập tên giấy. Không dùng status hỏi lại để né chấm fail khi nguồn đã đủ trả lời.

## Hành động là nội dung cần kiểm chứng

| Nội dung | Chứng cứ tối thiểu | Khi không đạt |
|---|---|---|
| Giấy bắt buộc nộp | Đúng thủ tục, nhóm đối tượng, phiên bản biểu mẫu và quy định tương ứng | Không xuất checklist bắt buộc; có thể nói cần xác định đúng thủ tục |
| Giấy giúp trao đổi | Hướng dẫn chính thức phù hợp; gắn nhãn tùy chọn nếu đúng nguồn | Không biến thành điều kiện tiếp nhận hồ sơ |
| Nơi nộp/nơi giải quyết | Nguồn thẩm quyền và hướng dẫn thủ tục; địa bàn, giai đoạn, ngày áp dụng | Không suy từ tên cơ quan hay một bài báo về khai trương |
| Địa chỉ/giờ/số liên hệ | Directory công khai còn được rà soát, đúng cơ quan và chức năng | Không đoán địa chỉ/số điện thoại; mở trang chính thức đã kiểm tra nếu có |
| Thời hạn/phí/số bản | Nguồn thao tác và điều kiện tính, ngoại lệ, mốc bắt đầu rõ | Không tính ngày cuối cá nhân từ ngày người dùng kể hoặc nhắc nhở tự động |
| Tóm tắt dễ hiểu | Toàn bộ điều kiện và hệ quả được chứng minh trong nguồn | Giữ thuật ngữ kèm giải thích hoặc giảm phạm vi trả lời |

Không dùng `Draft.next_steps` như kênh đưa việc phải làm không có citation. Với schema mới, phần nội dung hành động chuyển vào claim trước verify; `next_steps` cũ chỉ còn thao tác UI cố định không tạo nghĩa vụ pháp lý. Nếu giữ compatibility, serializer cũ nhận cùng nội dung đã verify, không sinh thêm câu.

## Nguồn và truy xuất

Đề xuất mở rộng source kinds `official_procedure`, `official_directory` trong cùng corpus. `official_procedure` chứng minh quy trình đã công bố, không tự chứng minh mọi điều kiện pháp lý; `official_directory` chỉ chứng minh thông tin liên hệ công khai, không tự chứng minh thẩm quyền. Kiểm tra cả nguồn pháp lý nền khi hành động phụ thuộc thẩm quyền hoặc điều kiện. Phân loại nguồn chi tiết trong CORPUS.

Thêm metadata stage/task/địa bàn vào catalogue và danh mục phục vụ lựa chọn. Không hard-filter loại hết luật chung hoặc văn bản chuyển tiếp khi người dùng chọn địa bàn. RRF hiện có tiếp tục hợp nhất các nhánh; không thêm reranker. Mở phụ thuộc cần thiết trong trần tools/rounds. Nếu nguồn cần thiết không lọt ngữ cảnh giới hạn, nêu thiếu nguồn; không cắt điều kiện để vừa prompt.

Hiện `applicability()` gán `context` cho news và kiểm tra legal dates cho nguồn khác. Vì vậy không chỉ thêm enum rồi cho directory thành `current`: cần evidence policy riêng theo kind/claim, ngày quan sát và phạm vi công bố. `source_fresh()` hiện có thể chặn toàn corpus trước graph; bản v2 đầu giữ cơ chế bảo thủ này. Thử nghiệm freshness theo nhóm phụ thuộc chỉ làm ở patch riêng sau khi có coverage chứng minh không bỏ sót luật tác động. Không nới freshness để cải thiện availability.

Policy bổ sung đề xuất: hành động về nơi nhận, liên hệ, giấy bắt buộc và thời hạn chỉ phát khi toàn bộ nguồn cần cho hành động có review `unchanged` trong giới hạn 7 ngày hoặc ngắn hơn đã định nghĩa. Snapshot override đang có không đủ để phát những hướng dẫn tác nghiệp này. Quy định snapshot vẫn có thể được giải thích trong phạm vi cho phép, với mốc nguồn thật; không tự thêm banner hoặc thay cấu hình trong đợt bàn giao thiết kế.

## Cẩm nang và danh bạ khi AI không khả dụng

V2 đầu ưu tiên mục hướng dẫn là điểm vào câu hỏi và liên kết nguồn đã duyệt. Không ship bản tóm tắt pháp lý tĩnh thiếu người duyệt để làm fallback. Có thể xuất bản thẻ hướng dẫn biên tập ở giai đoạn sau nếu từng câu được gắn nguồn/phiên bản và reviewer; nhãn rõ “hướng dẫn biên tập”, không giả là kết quả verifier runtime. Thẻ stale chuyển sang liên kết nguồn gốc, không dùng AI tạo lại tại frontend.

Danh bạ chỉ là projection dữ liệu công khai theo release từ cùng catalogue, không dịch vụ tra cứu bên ngoài runtime. Khi Groq bị quota hoặc generation tắt, đọc nguồn/danh bạ không gọi model và không tiêu public LLM quota. Nếu backend/DB cũng không sẵn sàng thì nói chưa tải được; không tuyên bố nguồn chắc chắn truy cập được hoặc hứa offline toàn ứng dụng.

## Quyền riêng tư, phiên bản và fingerprint

`CitizenNeed` chỉ ở bộ nhớ lượt hỏi; lựa chọn người dùng đã gửi thuộc nội dung hội thoại tại client. Nếu lưu lựa chọn để tiếp tục thì cùng bản ghi conversation, TTL tính từ khi tạo, không kéo dài mỗi lần mở. Server giữ corpus và metadata như trước. Không thêm bảng hồ sơ, câu hỏi người dùng, feedback tự do, trace hay answer cache. Không đưa lựa chọn nhạy cảm vào URL, localStorage analytics hoặc log.

Thêm module/policy/alias và metadata truy xuất mới vào `configuration_fingerprint`; thêm hash frontend presentation/answer schema vào identity đánh giá trải nghiệm để phân biệt cùng backend nhưng UI khác. Public metadata chỉ có phiên bản/hash/counts. Các benchmark synthetic có artifact trong `reports/`; hội thoại người thật không đi vào archive đó.

Rollout backend tương thích trước, client mới sau, bật UI theo capability server. Lịch sử cũ đọc được bằng renderer cũ; không sửa text/nguồn cũ thành đáp án v2. Mọi sửa đổi schema nguồn/claim cần roundtrip backup/restore riêng trên SQLite và PostgreSQL, runtime role check và cổng không lưu nội dung. Chưa tạo migration hoặc sửa database trong đợt thiết kế này.
