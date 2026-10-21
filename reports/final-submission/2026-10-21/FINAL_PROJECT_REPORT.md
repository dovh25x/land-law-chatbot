# BÁO CÁO ĐỒ ÁN CUỐI KỲ — BẢN THẢO

**TRƯỜNG ĐẠI HỌC PHENIKAA**

**Hanoi Land Law Assistant: Hệ thống tra cứu pháp luật về bồi thường, hỗ trợ và tái định cư cho Vành đai 4 tại Hà Nội bằng RAG có kiểm soát nguồn**

| Thông tin | Nội dung |
|---|---|
| Khoa/viện | |
| Tên học phần | |
| Mã học phần | |
| Họ và tên sinh viên | |
| Mã số sinh viên | |
| Giảng viên hướng dẫn | |
| Lớp/khóa | |
| Thời hạn nộp theo kế hoạch dự án | 23/10/2026 |
| Ngày chốt bản thảo/evidence | 21/10/2026 |

Thông tin hành chính được để trống theo yêu cầu. Repository chưa cung cấp syllabus, rubric hoặc mẫu báo cáo chính thức; không xem bản thảo này là xác nhận đã đáp ứng toàn bộ yêu cầu học phần. Các tiêu chí sản phẩm được đối chiếu với PRD, ADR và yêu cầu của người thực hiện. Trước khi nộp cần điền bìa và đối chiếu quy định học phần.

## Tóm tắt

Đồ án xây dựng một ứng dụng tra cứu tiếng Việt cho người dân liên quan đến thu hồi đất, bồi thường, hỗ trợ và tái định cư trong phạm vi Vành đai 4 tại Hà Nội. Hệ thống dùng FastAPI, LangGraph, Groq GPT-OSS 120B và E5 ONNX Q8 384 chiều; giao diện React/Vite, ingress Cloudflare Pages Function và kiến trúc triển khai Render–PostgreSQL/pgvector. Câu trả lời được biểu diễn bằng các claim có trích dẫn, qua kiểm tra nguồn, thời điểm và nội dung trước khi phát hành. Hệ thống không xác định thửa đất, tính tiền hoặc bảo đảm quyền lợi cá nhân.

Trên candidate cuối, evidence hiện có gồm 516 backend regression tests trên Python 3.14.4 và Python 3.12.15, 14 frontend unit tests, 100 Playwright fixture tests và build frontend thành công. Phase 4 bổ sung image local, kiểm bộ nhớ 512 MiB và PostgreSQL cách ly với migration/role/restore; chưa phải nghiệm thu cloud. Truy xuất offline trên SQLite đạt macro Recall@5 = 97,37% trên 19 câu có gold hợp lệ, tương ứng 20/21 gold chunks và micro Recall@5 = 95,24%. Các số này không đo độ đúng của câu trả lời pháp luật. Model inference trên candidate cuối chưa được thực hiện. Pilot Phase 3A trên fingerprint trước đó có C01 INCOMPLETE; C02/C03 chưa bắt đầu, được công bố NOT RUN. S06 của một cohort cũ giữ FAIL. Vì vậy, báo cáo không công bố RAGAS, độ đúng đáp án hoặc chất lượng production đã đạt. Đóng góp có thể kiểm chứng của đồ án là phần mềm, nguồn có xuất xứ, cơ chế kiểm soát phát hành và gói thực nghiệm công khai giới hạn; release cloud của candidate mới chưa đủ bằng chứng nghiệm thu. [E01–E08](EVIDENCE_INDEX.md)

## 1. Giới thiệu bài toán và động lực

### 1.1. Vấn đề thực tiễn

Một người có đất bị thu hồi thường cần biết mình nên đọc quy định nào, những điều kiện nào quyết định việc áp dụng và đâu là cơ quan/văn bản gốc để đối chiếu. Cùng một chủ đề có thể xuất hiện ở luật, nghị định, quy định địa phương và điều khoản chuyển tiếp. Tìm thấy từ khóa “bồi thường” chưa đủ để xác định quy tắc áp dụng cho một ngày hỏi hoặc một nhóm đối tượng.

Đầu vào của người dân thường không sử dụng đúng thuật ngữ pháp luật; ví dụ “sổ đỏ”, “đền bù” hoặc “chỗ ở mới”. Người dùng có thể chưa biết loại đất, nguồn gốc sử dụng hoặc ngày phê duyệt phương án. Nếu chatbot tự điền các dữ kiện còn thiếu, đáp án trôi chảy có thể làm người đọc hiểu nhầm quyền lợi. Thiết kế vì vậy ưu tiên khả năng mở nguồn, bảo toàn điều kiện và nêu giới hạn thay vì buộc mọi câu hỏi đều có câu trả lời khẳng định.

### 1.2. Câu hỏi nghiên cứu ở quy mô đồ án

Đồ án khảo sát ba câu hỏi: hệ thống có truy xuất được các đoạn nguồn đã gắn nhãn hay không; có giữ được căn cứ cần thiết khi đưa vào synthesis hay không; và có ngăn phát hành claim chưa đủ kiểm chứng hay không. Khả năng tạo đáp án đúng từ model thật là một câu hỏi riêng, chưa được xác nhận trên candidate cuối. Không dùng kết quả hai câu hỏi đầu để thay câu hỏi thứ ba.

### 1.3. Phương pháp và đóng góp

Phương pháp gồm xây dựng snapshot nguồn có provenance, triển khai một pipeline RAG hữu hạn, bổ sung regression cho lỗi đã quan sát và đánh giá theo từng lớp evidence. Đồ án do một sinh viên thực hiện; lựa chọn kỹ thuật ưu tiên tận dụng code đang có và hosting Free. Không có nghiên cứu người dùng có kiểm soát, chứng nhận pháp lý độc lập hoặc so sánh thực nghiệm giữa các framework.

## 2. Mục tiêu, đối tượng và giới hạn

### 2.1. Mục tiêu sản phẩm

Người dùng có thể hỏi bằng tiếng Việt, tra cứu nguồn, xem đoạn trích/locator, nhận câu hỏi làm rõ khi thiếu dữ kiện và nhận thông báo giới hạn khi chưa đủ chứng cứ. Giao diện hướng đến trải nghiệm hội thoại, có thư viện nguồn và lịch sử trên thiết bị. Kết quả cần kiểm tra được bằng văn bản gốc thay vì chỉ viện dẫn tên một cơ quan.

### 2.2. Phạm vi

Phạm vi vận hành là **Vành đai 4 tại Hà Nội và luật chung liên quan**. Không suy “pháp luật đất đai Hà Nội” thành bao phủ mọi dự án, mọi cơ chế thí điểm hoặc mọi trường hợp thu hồi. Tin dự án chỉ chứng minh bối cảnh/sự kiện được nguồn công bố, không chứng minh một hộ được nhận đất hay tiền.

Ba tình huống giả lập ngày 21/10/2026 trong Phase 2C/2 D tập trung vào điều kiện bồi thường, hỗ trợ ổn định đời sống và nhánh tái định cư. Chúng có các giả định về loại đất, giấy tờ, thời điểm và chuyển tiếp. Việc có đủ nguồn cho những giả định này không cho phép xác nhận một hồ sơ thật. [E05](EVIDENCE_INDEX.md#e05)

### 2.3. Ngoài phạm vi và giới hạn pháp lý

Không có chức năng GIS/xác định thửa đất, tính tiền bồi thường, upload hồ sơ, bảo đảm suất tái định cư, tài khoản hoặc đồng bộ lịch sử. Các cơ chế đặc thù chưa được review đầy đủ tiếp tục bị giới hạn. Bản snapshot không phải cơ sở dữ liệu pháp luật được cập nhật tự động. Receipt cho ngày 21/10 không tự có hiệu lực cho ngày 23/10.

Thông báo phù hợp khi trình diễn: “Ứng dụng hỗ trợ tìm và đọc nguồn trong phạm vi công bố; không thay thế việc giải quyết hồ sơ của cơ quan có thẩm quyền. Không nhập thông tin định danh hoặc hồ sơ riêng tư.” Không diễn đạt thành cam kết mọi câu trả lời đều chính xác.

## 3. Cơ sở lý thuyết

### 3.1. LLM và sinh văn bản có điều kiện

Mô hình ngôn ngữ sinh chuỗi bằng cách dự đoán token tiếp theo theo ngữ cảnh. Transformer sử dụng attention để xử lý quan hệ trong chuỗi. Một văn bản có xác suất cao không đồng nghĩa với mệnh đề đúng hoặc có hiệu lực pháp lý. Trong đồ án, LLM dùng dịch vụ bên ngoài; không huấn luyện hoặc fine-tune mô hình. Kiến trúc Transformer được trình bày trong Vaswani và cộng sự [T1](#tài-liệu-tham-khảo).

### 3.2. Retrieval-Augmented Generation

RAG kết hợp nguồn tri thức truy xuất được với mô hình sinh; nghiên cứu của Lewis và cộng sự là một mốc tham khảo cho cách kết hợp này [T2](#tài-liệu-tham-khảo). Đồ án vận dụng ý tưởng đưa chứng cứ vào ngữ cảnh, không tái hiện mô hình huấn luyện hoặc các benchmark trong bài báo. Retrieval sai, thiếu ngữ cảnh hoặc synthesis diễn giải sai vẫn có thể tạo kết luận sai dù đã áp dụng RAG.

### 3.3. Embedding, hybrid retrieval và RRF

Embedding ánh xạ văn bản sang vector để so sánh các cách diễn đạt gần nhau. Họ mô hình multilingual E5 là nguồn tham khảo về biểu diễn đa ngôn ngữ [T3](#tài-liệu-tham-khảo). Implementation của đồ án ghim checkpoint và preprocessing cụ thể; chất lượng E5 trên benchmark khác không được chuyển thành chất lượng tiếng Việt pháp lý của dự án.

Hybrid retrieval cần cả tìm số hiệu/điều khoản và tìm diễn đạt tự nhiên. Reciprocal Rank Fusion hợp nhất vị trí trong nhiều bảng xếp hạng theo công thức:

`RRF(d) = Σ_r 1 / (k + rank_r(d))`.

Cormack, Clarke và Büttcher trình bày RRF [T4](#tài-liệu-tham-khảo). Trong source hiện tại, k=60; kết quả còn có các boost và quy tắc phạm vi riêng. Do đó hệ thống không phải thí nghiệm RRF thuần, và chưa có ablation chứng minh từng nhánh làm tăng Recall.

### 3.4. Đánh giá theo lớp

Truy xuất, tính đầy đủ của context, provenance của citation, entailment và đáp ứng tác vụ là các thuộc tính khác nhau. Ragas là một framework nghiên cứu đánh giá RAG [T5](#tài-liệu-tham-khảo). Repository có evaluator claim-support tùy biến lấy cảm hứng từ faithfulness, **không chạy framework RAGAS**. Một chỉ số lấy cảm hứng từ khái niệm không được mang tên kết quả của framework chưa sử dụng.

## 4. Requirements specification

Yêu cầu được trích từ PRD và ràng buộc dự án, không tự gán trọng số hoặc điểm của rubric học phần chưa có. [E09](EVIDENCE_INDEX.md#e09)

| ID | Yêu cầu | Implementation/evidence | Trạng thái ở candidate |
|---|---|---|---|
| FR01 | Hỏi bằng tiếng Việt và làm rõ dữ kiện | Agent/citizen logic; unit và UI fixtures | Phần mềm có; chất lượng model chưa xác nhận |
| FR02 | Tra cứu điều khoản, nguồn và quan hệ văn bản | Hybrid search/open_article/check_effectivity | Có source và đo retrieval SQLite |
| FR03 | Kết luận có citation kiểm chứng | Claims, synthesis ledger và verifier | Có guard; chưa có model-answer pass hiện hành |
| FR04 | Hỏi tiếp, không xem history là chứng cứ | Request history giới hạn và retrieval lại | Có regression; không khẳng định public model flow đã đạt |
| FR05 | Xem nguồn khi generation không khả dụng | Thư viện và source panel | UI fixture đạt; public candidate chưa kiểm |
| FR06 | Lịch sử trên thiết bị, xóa/hết hạn | IndexedDB, không server replay | Có implementation và regression |
| NFR01 | Không phát draft chưa verify | Graph/SSE contract | Regression đạt |
| NFR02 | Hữu hạn ngân sách và thời gian | 6 LLM/12 tools/2 rounds/1 repair/90 s | Regression đạt; quota provider vẫn có thể chặn |
| NFR03 | Nguồn chưa xác minh không khẳng định luật hiện hành | Source gate và scoped receipts | Fail-closed; không toàn corpus fresh |
| NFR04 | Bảo vệ secret và hạn chế lưu dữ liệu | Ingress, quotas, logging metadata, client history | Kiểm tra local; cấu hình production chưa xác minh mới |
| NFR05 | Reproducibility | Suite/hash/corpus/fingerprint/attempt | Có asset và index; cần giao đủ asset khi nộp |
| NFR06 | Website cloud hoạt động và khôi phục được | Workflow/Render/Pages/PG/migrations | Có cấu hình; candidate mới NOT TESTED công khai |

Không dùng số unit tests hoặc việc có file triển khai để đánh dấu FR03/NFR06 hoàn thành về chất lượng thực tế.

## 5. System architecture và lựa chọn công nghệ

### 5.1. Kiến trúc triển khai

![Kiến trúc hệ thống hiện có](../../../docs/diagrams/architecture.svg)

Sơ đồ tái sử dụng asset của repository, xuất theo diagram-design revision đã ghim; [source HTML](../../../docs/diagrams/architecture.html) và [quy trình xuất](../../../docs/diagrams/README.md) được giữ nguyên. Đây là kiến trúc trong source, không phải bằng chứng candidate đã deploy.

Luồng dự kiến khi production: React/Vite → Cloudflare signed ingress → FastAPI trên Render → PostgreSQL/pgvector; Groq thực hiện inference, E5 chạy local CPU. Ingest/OCR nằm ngoài runtime chat. SQLite dùng cho local và các kiểm tra offline đã công bố. [E10](EVIDENCE_INDEX.md#e10)

### 5.2. Trách nhiệm thành phần

| Thành phần | Trách nhiệm thực tế |
|---|---|
| React/Vite | Composer, trạng thái chat, source panel, trace, lịch sử và responsive |
| Pages Function | Proxy cùng origin, ký HMAC, chuyển tiếp SSE |
| FastAPI | Phiên, validation, signed ingress, quotas, lease, deadline và SSE |
| LangGraph/Agent | Plan, tools, synthesis, verify, repair hoặc finish |
| GroqProvider | JSON request, retry hữu hạn, usage và operator test ledger |
| Store/retrieval | Corpus theo phiên bản, tìm kiếm, quan hệ và metadata |
| Scripts/migrations | Chuẩn bị nguồn, kiểm tra, đánh giá, đóng gói và vận hành |

### 5.3. LangGraph + Groq thay cho LlamaIndex + ChatGPT API

Theo bối cảnh do người thực hiện cung cấp, định hướng ban đầu có nhắc LlamaIndex và ChatGPT API, đồng thời cho phép lựa chọn khác nếu phù hợp. Repository không có văn bản rubric/phê duyệt gốc để đối chiếu. Báo cáo giải thích quyết định kỹ thuật, không thay thế việc sinh viên xác nhận yêu cầu học phần.

LangGraph đang được dùng để biểu diễn các nhánh kiểm chứng, retry và dừng có giới hạn; FastAPI, provider và store đã tích hợp với graph. Groq GPT-OSS 120B là provider/model đang vận hành trong source; E5 ONNX hỗ trợ inference embedding CPU và contract cố định. Giữ các thành phần này tránh chuyển đổi framework/provider hoặc thay corpus trước deadline. Những lý do đó là về tính liên tục và khả năng hoàn thành của dự án, **không phải kết luận LangGraph/Groq tốt hơn LlamaIndex/ChatGPT**. Chưa có benchmark cùng điều kiện để đưa ra kết luận so sánh về độ đúng, chi phí hoặc latency. [E11](EVIDENCE_INDEX.md#e11)

### 5.4. Ranh giới kiến trúc

Chỉ có một pipeline. Không có multi-agent, reranker, fine-tuning, GIS hoặc dịch vụ mới trong bản triển khai. Graph quản lý trạng thái của một lượt; history dài hạn thuộc client. Một phần câu hỏi định hướng hoặc fact nguồn có thể được xử lý tất định, nên không suy có LLM inference chỉ từ việc nhận được một đáp án.

## 6. Legal corpus, preprocessing, chunking và provenance

### 6.1. Snapshot và vai trò nguồn

Candidate dùng `corpus-1afca764aa6692e0`, gồm 60 document records và 7396 chunks. Payload SHA256 là `7ce7956ae35c7006b5bfd7d10d516fa9e8e47fe2f073e471ceecbb34b412d317`. Đây là quy mô snapshot, **không phải 60 văn bản đều fresh hoặc được phép áp dụng hiện hành**. Corpus/receipt/source-policy checksum trong freeze manifest giúp đối chiếu đúng phiên bản. [E01](EVIDENCE_INDEX.md#e01)

Nguồn có phân loại vai trò: pháp luật, hồ sơ dự án/tin chính thức và nguồn thủ tục/danh bạ khi đủ review. Metadata giữ tài liệu, số hiệu, jurisdiction, URL, checksum, ngày kiểm tra và quan hệ văn bản. URL trong allowlist hoặc HTTP200 chỉ là một phần provenance, không chứng minh điều khoản còn áp dụng.

### 6.2. Xử lý văn bản

Nguồn HTML/PDF hoặc ảnh được xử lý ngoại tuyến, có quarantine khi thiếu điều kiện chất lượng. OCR cần đối chiếu và trạng thái review; không được xem văn bản OCR chưa kiểm là chứng cứ chắc chắn. Với nhiều PDF hoặc ảnh nguồn, metadata ánh xạ đúng trang vật lý/URL và checksum. Bản tổng hợp từ ảnh không được mô tả là PDF ký số gốc.

Chunk gắn locator và trang, có liên kết cha–con để giữ tiêu đề/ngữ cảnh. Implementation vừa nhận diện điều/khoản vừa giới hạn kích thước; không thể mô tả mọi chunk là một đơn vị pháp luật hoàn chỉnh. Một đoạn con có thể thiếu chủ thể hoặc điều kiện ở đoạn trước. Phase 2D bổ sung context selection để giữ các đơn vị bắt buộc và từ chối citation không được đưa vào synthesis. [E06](EVIDENCE_INDEX.md#e06)

### 6.3. Embedding contract

Contract là `multilingual-e5-small-onnx-q8-window-v1`,384 chiều. Model/tokenizer được ghim revision và SHA256; inference ONNX CPU, prefix query/passage, masked/window pooling và chuẩn hóa vector theo implementation. Passage window tối đa 512 tokens, query 128, overlap 64; các đơn vị này là giới hạn encoder, khác với ngân sách context 7000 ký tự của synthesis. Không đổi model hoặc re-embedding để cải thiện pilot. [E12](EVIDENCE_INDEX.md#e12)

### 6.4. Freshness, applicability và scoped receipt

Freshness là trạng thái đã rà soát theo thời hạn/checksum; applicability là khả năng áp dụng theo văn bản, ngày hỏi, quan hệ sửa đổi và chuyển tiếp. Hai khái niệm không thay thế nhau. F01 sửa hành vi snapshot override để nguồn **đã biết thay đổi** không được dùng phát hành claim chỉ vì bật snapshot. Nguồn quá hạn, changed hoặc unknown không được nhập nhằng thành fresh. [E13](EVIDENCE_INDEX.md#e13)

Receipt giới hạn `chunk_checksums` và khoảng ngày hỏi, gắn review thật và source policy. Sau restore, thiếu receipt phải fail-closed; chỉ áp lại receipt hợp lệ mới mở đúng phần review. Tại Phase 3B, cấp document vẫn 59 stale/1 unknown; gate usable nhờ phần được duyệt theo scope, không phải gia hạn toàn 60 document records.

| Tình huống hiện hành giả lập | Căn cứ trong phần review | Hạn chế quyết định |
|---|---|---|
| C01: điều kiện và hình thức bồi thường | Luật 31/2024:95,98; NQ 254/2025:3(10) và chuyển tiếp được review | Đã có source capture ở cohort trước; model attempt INCOMPLETE, không xác nhận quyền lợi |
| C02: hỗ trợ cho giả định đất nông nghiệp, thu hồi 40%, không di chuyển | Luật 31:108; QĐ 40/2026:17; NĐ 49:11 và các sửa đổi liên quan | Context 3/3,5070 ký tự; chưa có model answer đạt |
| C03: tái định cư đối với giả định thu hồi hết đất ở tại xã | Luật 31:111(4); NĐ 88:11; NĐ 226:7; NĐ 49:16; QĐ 40:21 | Context 7/7,6981 ký tự; chưa có model answer đạt; không cam kết suất/diện tích |

Bảng mô tả phạm vi review ngày 21/10, không đưa ra kết luận tư vấn mới. Nguồn chính thức, điều khoản chuyển tiếp, ngoại lệ và giới hạn xác minh nằm trong [biên bản pháp luật Phase2C](../../phase2c-current-20261021/LEGAL_REVIEW.md). Không suy một điều vẫn áp dụng chỉ vì có trong snapshot.

## 7. Retrieval, synthesis, verification và citation

### 7.1. Truy xuất

Các công cụ chỉ đọc phục vụ search_law, search_project, open_article, check_effectivity và normalize_place. Query có chuẩn hóa thuật ngữ và viện dẫn; search kết hợp lexical, vector, heading, exact-reference và candidate liên quan thay thế. PostgreSQL dùng full-text/pgvector; SQLite có lexical scoring/vector implementation khác. RRF và boost tạo thứ tự ứng viên; mở điều và quan hệ pháp lý là bước riêng trong agent.

### 7.2. Từ retrieved đến synthesis

Không đồng nhất ba tập: **retrieved** là ứng viên tìm thấy, **admitted** là passage được kiểm nguồn cho thời điểm hỏi, **synthesis** là phần thực sự đưa vào tạo draft. Sau evidence cap/context budget, nguồn có trong retrieval vẫn có thể không được model thấy. Ledger lưu mapping để verifier chỉ dùng passage đã xuất hiện. Alias C1,C2 là ID trong payload, không phải quyền được phát hành.

Context selection có metadata clause spans và dependencies cho dẫn chiếu chủ thể/điều kiện. Ví dụ một khoản nói “các trường hợp tại khoản…” phải được đọc cùng phần chủ thể được dẫn, không chuyển danh sách điều kiện OR thành mọi nhóm đối tượng. Metadata hỗ trợ việc đọc, không tự xác nhận đủ bằng chứng hoặc thay nội dung luật. [E06](EVIDENCE_INDEX.md#e06)

### 7.3. Tạo draft và kiểm chứng

LLM trả JSON theo schema, biểu diễn claim và citation IDs. Structural verifier kiểm tra phạm vi, điều kiện và mâu thuẫn có thể xác định; semantic verification chỉ diễn ra khi đáp ứng điều kiện gọi model. Quote/citation matching xác minh xuất xứ nhưng không tự chứng minh entailment. Những kết luận về chủ thể, tiền, thủ tục, thời hạn hoặc cơ quan phải có nguồn tương ứng.

Synthesis → verify → repair/finish nằm trong graph hiện có. Claim không được duyệt đủ hoặc còn issues bị loại cùng phần phụ thuộc, không tự nối một điều kiện chưa được verify vào cuối đáp án. Nếu mất nội dung có nghĩa thì hỏi lại hoặc từ chối. Các guard có thể false positive; S06 cho thấy cần phân biệt guard từ chối với bằng chứng model chắc chắn sai ở mọi phần.

### 7.4. Ngân sách và lỗi API

Mỗi lượt giữ 6 requests LLM gồm retry,12 tools,2 retrieval rounds,1 repair và 90 giây. Groq max completion 2048; planner low reasoning, draft/verification medium. Phase 3B thêm ledger operator phân biệt confirmed_usage, estimated_usage, reserved_budget và remaining_test_budget, tách khỏi quota provider. Provider format failures được retry có feedback định dạng chung và giới hạn; không nhận failed_generation làm đáp án hoặc hạ schema. [E02](EVIDENCE_INDEX.md#e02)

Ledger giữ upper bound cho response thiếu usage, kể cả 429/400. Reservation vẫn dùng byte UTF-8 của request cộng allowance và max output; chưa có căn cứ giảm bằng tokenizer khác. Trong allocation Phase 3A,4829 confirmed +47330 estimated để lại 7841, không đủ reservation 19788 của C02. Không chạy thử để xem có vượt hay không, không tạo output mới để tự cấp lại ngân sách.

## 8. Frontend, backend, database và cloud

### 8.1. Trải nghiệm người dùng

UI hội thoại có trạng thái loading, hủy, lỗi, hỏi làm rõ và nguồn. Source panel hỗ trợ so sánh trên desktop, modal trên màn hình nhỏ; citation mở đúng đoạn nguồn và đường dẫn gốc. Thiết kế tham chiếu Figma nhưng hình minh họa thiết kế không phải transcript model. Trace chỉ gồm sự kiện thực thi quan sát được. [E14](EVIDENCE_INDEX.md#e14)

IndexedDB giữ tối đa 7 ngày, có giới hạn số cuộc/message/dung lượng. Bearer token phiên nằm trong sessionStorage/bộ nhớ tab, không phải lịch sử dài hạn. Không có đồng bộ thiết bị; mất stream không có server replay đáp án. Giao diện không tự gửi lại POST chat để che lỗi.

### 8.2. Backend và dữ liệu

FastAPI quản lý session token, request ID, quotas, lease và SSE. Một lượt đang chạy mỗi phiên và concurrency toàn hệ thống hữu hạn. Store giữ corpus, review và metadata thực thi; server không giữ messages, answer cache hoặc trace chi tiết. Migration 006 xóa payload cũ và thu hồi quyền runtime; đây không phải migration có thể đảo để khôi phục lịch sử. Chỉ database riêng được dùng để test restore.

PostgreSQL có schema/migration, role và chỉ mục 384 chiều; migration có thể vẫn cho phép vector archive kích thước cũ. Runtime phải ghim contract 384 và không trộn contract chỉ vì schema lưu được nhiều kích thước. Sau chấp thuận bổ sung Docker, Phase 4 kiểm PostgreSQL 16.15/pgvector 0.8.7 trong container mới: migrations 001–006, runtime role, session lease và restore corpus 60 records/7396 chunks sang DB thứ hai đều đạt. Restore thiếu receipts fail-closed, reapply hợp lệ mở gate; không có server conversation rows. Fingerprint PG được kiểm local là `2229a1b298052e51b80d1d46530ca9a5ba580f5bc1b04be90cecdf0e15190c6d`. Chưa chạy PG retrieval benchmark 19 câu, full backend suite trên PG hoặc Supabase integration. [E15](EVIDENCE_INDEX.md#e15)

### 8.3. Triển khai cloud

Source có Dockerfile, CI và workflow Pages/Render; cấu hình Free được giữ. Serving image Phase 4 đã build trên Python 3.12.15, chạy non-root và kiểm checksum model/fingerprint. Kiểm bộ nhớ đạt 382,66 MiB peak RSS dưới giới hạn 512 MiB với lifespan,8000 headingfixtures và hai query embedding đồng thời; đây không phải load test mọi tình huống. Lần chạy tests trong serving image có 513 pass/3 fail do thiếu Git/notebook; giữ log, sau đó dùng testtools image riêng bổ sung Git và mount notebook, đạt 516/516. Không thay serving image để thêm công cụ test. Python 3.14.4 có 516 PASS từ Phase 3B; không cộng hai lần thành 1032 test độc lập. Frontend Node 24, local locks khớp installed packages và npm manifest; CI trên source commit mới vẫn chưa chạy.

Candidate chưa commit và chưa deploy trong các phase cuối. Domain được ghi trong README là địa chỉ dự án lịch sử, không xác nhận đang phục vụ source/hash/corpus mới. Public E2E và deployed fingerprint của candidate vẫn NOT TESTED. `.dockerignore` Phase 4 chỉ loại tài liệu nộp và backup replay trùng khỏi image context; dữ liệu gốc được giữ. Image identity, các path bị loại và public report inputs còn đủ được ghi trong Docker receipt; build local chưa phải registry release. [E16](EVIDENCE_INDEX.md#e16)

## 9. Security, privacy, legal và ethical considerations

Signed ingress HMAC đặt ranh giới giữa Cloudflare và backend; backend không tin IP client tự khai. Turnstile xác minh server-side khi tạo phiên; quota public tách usage operator, cả hai vẫn chịu quota Groq. Không đưa secret vào VITE_*, source, response hoặc log. Unit tests không xác nhận các secret/hostname và policy đang đúng trên cloud.

History và citation từ browser là dữ liệu không đáng tin; không coi chúng là căn cứ pháp luật hoặc quyền gọi operator. Input/document không được cấp quyền thực thi shell/SQL/URL tùy ý. Markdown không thực thi HTML. Server log metadata phục vụ vận hành; nội dung vẫn truyền qua dịch vụ để xử lý, nên không được quảng cáo “không dữ liệu nào rời thiết bị”. Cấu hình Zero Data Retention của provider chưa được kiểm tra.

Rủi ro đạo đức gồm người dùng tin quá mức vào đáp án, nhầm giả định thành quyền lợi và lộ hồ sơ cá nhân. Cách giảm rủi ro đã triển khai là phạm vi hẹp, source/citation guards, từ chối và hạn chế lưu server. Cần review pháp lý độc lập và kiểm thử với người dùng trước khi khẳng định tác động xã hội. Không tạo transcript giả hoặc giấu các ca fail/incomplete để trình diễn.

## 10. Experimental setup, datasets và metrics

### 10.1. Thiết lập và tính tái lập

Runtime SQLite cuối: `1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d`. Git HEAD `117e7bd2c4a320c3d02256dfdabf858180b47dbf` chỉ là base commit; các bản vá vẫn ở working tree. Freeze manifest riêng mô tả source tree sau packaging, dependency locks và trạng thái candidate_commit=null. Không dùng base commit thay cho toàn code đã kiểm thử.

Bộsmoke 20 +supplemental 4 +natural 8 giữ nguyên bytes/checksum. Registry citizen-v 2-draft chưa executable; không gộp vào 32 ca đã khóa. C01–C03 là acceptance/pilot giả lập riêng, không thay câu thất bại của bộ khóa. Snapshot, receipt và context phải cùng cohort. Các tệp corpus/raw/model lớn được liên kết thay vì nhân bản; nộp Git source đơn lẻ chưa đủ nếu thiếu asset ignored cần để tái lập.

### 10.2. Recall@5

Với `G_i` là tập gold chunk của câu i và `R_i^5` là năm hits đầu của đúng phép đo:

`Recall@5_i = |G_i ∩ R_i^5| / |G_i|`.

`Macro Recall@5 = (Σ_i Recall@5_i)/n`.

`Micro Recall@5 = (Σ_i |G_i ∩ R_i^5|)/(Σ_i |G_i|)`.

Mẫu số 19 gồm 10 smoke,3 supplemental,6 natural. S06 loại trước chạy theo chỉ dẫn không chạy lại;12 ca không có positive gold không có mẫu số Recall. Một câu có gold để tìm nguồn không nhất thiết là câu answerable về quyền lợi. Không dùng tập 19 này để suy nhãn answerability hoặc accuracy cho cả 32 ca.

### 10.3. Các phép đo khác

| Nhóm | Định nghĩa/phương pháp | Trạng thái trên runtime cuối |
|---|---|---|
| Context completeness | Đoạn bắt buộc còn đầy đủ trong payload và snapshot | Có capture C02/C03; không suy model đúng |
| Citation integrity | ID/document/locator/excerpt/checksum thuộc snapshot/corpus | Có unit và source-quote fixture; không có model citation aggregate |
| Citation Accuracy | Review quan hệ chứng minh của từng claim–citation, đúng phạm vi/ngày/ngoại lệ | NOT MEASURED cho model cuối |
| Answer Correctness | Reviewer đối chiếu đáp án với proposition/rubric đã khóa | NOT MEASURED cho model cuối |
| RAGAS Faithfulness | Chạy RAGAS thật, ghim version/judge/context và denominator | NOT MEASURED; không có RAGAS run |
| Custom sampled faithfulness | Evaluator riêng phân tách/chấm claim-support | NOT MEASURED cho runtime cuối; có lịch sử khác fingerprint |
| Safety/abstention | Ca đúng nhánh và false abstention trên answerable | Unit/fixture có; model rate cuối NOT MEASURED |
| Latency model/public | Tách thời gian request, whole-turn, cooldown và cold start | NOT MEASURED trên final/public |

Refusal của câu answerable không được chấm đúng. Không có claim/citation thì faithfulness/citation integrity không tự bằng 1. Cần sidecar answerability được review và gắn checksum trước khi tính Answerable Coverage/False Abstention Rate; không sửa gold để điền nhãn sau khi xem kết quả. [Phương pháp và mẫu số chi tiết](EVALUATION_SUMMARY.md)

## 11. Results, failure analysis và discussion

### 11.1. Software và retrieval trên candidate cuối

| Evidence | Kết quả | Phạm vi |
|---|---:|---|
| Backend regression | 516 PASS mỗi môi trường | Python 3.14.4 local và Python 3.12.15 testtools Docker; HTTP thật bị chặn |
| Frontend unit | 14 PASS | Source UI hiện tại |
| Frontend build | PASS | TypeScript/Vite |
| Playwright | 100 PASS | Local desktop/mobile, API fixtures |
| Macro Recall@5 | 97,37% | 19 câu SQLite |
| Gold hits / gold labels | 20/21 | Micro Recall@5=95,24% |
| Context C02 | 3/3;5070 ký tự | Payload synthesis đầy đủ |
| Context C03 | 7/7;6981 ký tự | Sát giới hạn 7000 ký tự |
| Image memory check |382,66 MiB peak RSS |512 MiB hard cap, offline fixtures; không load test public |
| PostgreSQL local | PASS | Migration/role/lease/corpus restore, không cloud hoặc model |

N03 có Recall 0,5 vì thiếu gold parent trong top 5 dù child liên quan xuất hiện. Không đổi nhãn hoặc tính tương đương parent/child để làm kết quả 100%. Các chỉ số retrieval chỉ dùng query gốc, không cộng evidence sau agent expansion. [E03](EVIDENCE_INDEX.md#e03)

### 11.2. Model và các cohort lịch sử

| Cohort | Kết quả giữ nguyên | Điều không được suy ra |
|---|---|---|
| S06 cuối, fingerprint 2dab4dde… | FAIL;2 HTTP200;8104 tokens; không phát claim | Không coi repair có cải thiện là pass; không gán kết quả cho 1697… |
| Phase 3A, fingerprint 37d2fb54… | C01 INCOMPLETE; draft đầu không đủ phát hành | HTTP200 không đồng nghĩa answer correctness |
| Phase 3A C02/C03 | NOT RUN,0 attempts/0 requests | Không coi placeholder INCOMPLETE trong raw receipt là inference đã thất bại |
| Phase 3B, fingerprint 1697d9de… |0 model requests | Không có model correctness/faithfulness mới |

Phase 3A C01 gửi đủ 4/4 đoạn bắt buộc nhưng draft thiếu citation NQ 254 và rút gọn mất điều kiện của nhánh Điều 111. Structural verifier chặn; có một issue nhạy với cách diễn đạt khoản 1 nên không được dùng issue đó một mình để khẳng định mọi mô tả chủ thể sai. Repair gặp 429 TPM, rồi 400 JSON; request tiếp theo bị budget chặn.0 claim/citation được phát hành. [E07](EVIDENCE_INDEX.md#e07)

C01 mất 34,858 giây toàn ca; ba HTTP latency 3756/148/4941 ms thuộc attempt dở dang. Không biến số này thành latency đáp án thành công hoặc public p95. Usage 4829 là xác nhận;52159 là tổng kế toán bảo thủ có unknown, không phải số token thực đo. Header requests là RPD, token là TPM; không có bằng chứng vượt RPM/TPD hoặc double-retry.

### 11.3. Integrity không thay correctness

Source-quote fixture cuối phát hành một claim/một citation nằm trong nguồn đã review. Đây là kiểm tra luồng, có semantic judge fixture, không inference model. Trong cohort 80512d4e… trước final ledger-resume fix, coverage fixture 9/11 khớp status; C02/C03 bị từ chối vì cite child không xuất hiện trong synthesis snapshot chọn parent. Báo cáo giữ hai FAIL và không chuyển 9/11 thành kết quả model hoặc score của fingerprint 1697… . [E04](EVIDENCE_INDEX.md#e04)

### 11.4. Faithfulness lịch sử

Cohort `c4f0c661…` có custom sampled faithfulness 0,9231 trên 13 claims thuộc 6/8 case mẫu; cohort 800c96ba… không chấm được case nào. Cả hai là evaluator riêng, dùng cùng model làm judge, không phải RAGAS, không phải independent legal certification và không được gộp vào candidate cuối. Giữ denominator, trường hợp không áp dụng/lỗi và artifact gốc thay vì chọn số cao làm kết luận tổng. [E08](EVIDENCE_INDEX.md#e08)

### 11.5. Thảo luận và threats to validity

Retrieval cao nhưng model chưa phát hành được kết quả hợp lệ là một khoảng cách thực nghiệm quan trọng. Tìm được đoạn nguồn là điều kiện cần, chưa đủ; selection, synthesis, guard và API budget đều có thể làm lượt không hoàn tất. Fail-closed bảo vệ phát hành nhưng có thể gây false abstention. Vì vậy cần báo cả chất lượng nội dung và khả năng thực thi, không tối ưu một ca để thay cho bằng chứng tổng thể.

Các đe dọa gồm mẫu nhỏ do tác giả chọn, tương quan giữa người viết code và người gán nhãn, nhiều vòng chỉnh sửa trên cùng tập, thiếu holdout/người review độc lập, khác biệt SQLite/PG, snapshot chỉ có thời điểm áp dụng nhất định, judge cùng model, cắt ngữ cảnh và quota gây censoring. [Bảng đầy đủ và cách giảm rủi ro](KNOWN_LIMITATIONS.md)

## 12. Kết luận và hướng phát triển

Đồ án đã xây dựng một hệ thống tra cứu pháp luật có giao diện, pipeline, provenance, guards, test và quy trình đóng gói/evaluation có phiên bản. Kết quả xác nhận được là hoạt động phần mềm offline, khả năng truy xuất trên snapshot SQLite và kiểm soát phát hành theo nguồn. Chưa đủ bằng chứng xác nhận model giải quyết ổn định ba tình huống hiện hành trên candidate cuối hoặc website cloud mới đạt nghiệm thu.

Phần còn lại trước phát hành là chốt source commit sau review, CI/registry image trên SHA đó, PostgreSQL cloud/role/restore, tính phù hợp receipt cho ngày demo và public E2E. Image và PostgreSQL local đã kiểm chỉ giảm blocker môi trường, không xác nhận production hoặc model. Không tiếp tục tối ưu C01/S06, thay model/framework, cấp lại budget hoặc hạ verifier trong Phase 4. Nếu không có thêm inference hợp lệ, buổi bảo vệ phải demo nguồn/retrieval và giới hạn đã kiểm chứng, kèm báo cáo thiếu metrics thay vì transcript giả.

Hướng nghiên cứu sau học phần có thể là tăng dữ liệu review độc lập, mở rộng corpus có quản trị, đo false abstention và usability với người dùng phù hợp. Đây là đề xuất tương lai, không phải chức năng đã hoàn thành hoặc kế hoạch tự triển khai trong candidate này.

## Tài liệu tham khảo

- **T1.** Vaswani, A. và cộng sự (2017). *Attention Is All You Need*. [arXiv:1706.03762](https://arxiv.org/abs/1706.03762).
- **T2.** Lewis, P. và cộng sự (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. [arXiv:2005.11401](https://arxiv.org/abs/2005.11401).
- **T3.** Wang, L. và cộng sự (2024). *Multilingual E5 Text Embeddings: A Technical Report*. [arXiv:2402.05672](https://arxiv.org/abs/2402.05672).
- **T4.** Cormack, G.V., Clarke, C.L.A., Büttcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*. [Bản tác giả, University of Waterloo](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf).
- **T5.** Es, S., James, J., Espinosa-Anke, L., Schockaert, S. *Ragas: Automated Evaluation of Retrieval Augmented Generation*. [arXiv:2309.15217](https://arxiv.org/abs/2309.15217), bản đầu 2023.
- **T6.** Groq. [Structured Outputs](https://console.groq.com/docs/structured-outputs), [Rate Limits](https://console.groq.com/docs/rate-limits); tham khảo cơ chế API, không dùng quota mặc định thay evidence của tài khoản.
- **T7.** Repository: [PRD](../../../docs/PRD.md), [Architecture](../../../docs/ARCHITECTURE.md), [ADR](../../../docs/adr/README.md), [Evaluation](../../../docs/EVALUATION.md), [Operations](../../../docs/OPERATIONS.md).
- **T8.** [Biên bản nguồn chính thức Phase2C và URL văn bản](../../phase2c-current-20261021/LEGAL_REVIEW.md), ngày review 21/10/2026; không xác nhận hiệu lực cho ngày khác.
- **T9.** [Evidence index và checksum](EVIDENCE_INDEX.md), [Freeze manifest](freeze-manifest.json). Các số thực nghiệm trong báo cáo lấy từ các artifact được chỉ rõ; không từ tài liệu lý thuyết.

## Phụ lục: bản đồ tài liệu nộp

[Evaluation summary](EVALUATION_SUMMARY.md), [known limitations](KNOWN_LIMITATIONS.md), [slide outline](SLIDE_OUTLINE.md), [demo script](DEMO_SCRIPT.md), [release checklist](RELEASE_CHECKLIST.md), [submission checklist](SUBMISSION_CHECKLIST.md) và [code freeze/inventory](CODE_FREEZE.md) là các phần kèm theo. Báo cáo Markdown cần được sinh viên chuyển sang định dạng nộp chính thức và kiểm tra lại số trang, hình, mục lục và trích dẫn theo mẫu học phần; không giả định đã có bản PDF/DOCX hoặc bộ slide hoàn chỉnh.
