# Phase 3B — API Reliability Recovery & Release Preflight

**NOT READY cho pilot mới nếu tiếp tục dùng allocation 60.000 tokens của Phase3A.** Phần ngân sách còn lại theo cách tính bảo thủ là **7.841**, nhưng request đầu C02 cần reservation **19.788**. Không có căn cứ để hoàn dự phòng của hai lỗi thiếu usage, và không coi thư mục output mới là được cấp lại ngân sách. Các bản vá kỹ thuật đã qua regression; điều này chưa giải quyết được thiếu ngân sách đã xác minh hoặc chứng minh chất lượng model. **Release/deploy cũng NOT READY.**

Không gọi Groq/judge API trong Phase3B, không mở attempt model C01/S06, không sửa model/embedding/corpus/gold/verifier, không commit/push/deploy hoặc truy cập database cloud. Các bài unit dùng fixture vẫn chạy trong bộ regression; chúng không phải attempt model mới. Timebox bắt đầu **07:39:24 UTC 21/10/2026**, kết thúc công việc được ghi tại `completion.json`, hạn tối đa08:39:24.

**1. Root causes: sự kiện đã xác nhận và phần chưa biết**

| Vấn đề | Xác nhận từ evidence | Không đủ bằng chứng để kết luận |
|---|---|---|
| HTTP429 | Request02 Phase3A trả `rate_limit_exceeded`, type `tokens`, body ghi **TPM**, Limit8000, Used4254, Requested4198. `Retry-After=4`, remaining tokens3746, reset31.904s. Request03 gửi sau ít nhất4.497s. | Không xác định mức sử dụng RPM/TPD hoặc hoạt động khác trong tổ chức tại thời điểm đó. Không coi số liệu tài liệu mặc định là quota thực của tài khoản. |
| JSON | Request03 trả **HTTP400 `json_validate_failed` / `invalid_request_error` từ Groq**, trước parser JSON/Pydantic của ứng dụng. Request đã dùng `json_schema`, `strict=true`, `tool_choice=none`, không có native tools hoặc streaming. Request01 cùng cấu hình đã HTTP200. | Không lưu `failed_generation`; không thể xác định JSON lỗi cú pháp, sai trường, bị giới hạn output hay lỗi provider cụ thể. Không có bằng chứng lỗi tool-call parsing hoặc schema hoàn toàn không tương thích. |
| Budget stop | Request01 usage4829. Request02/03 không có usage nên mỗi request giữ upper bound23665. Tổng bảo thủ52159; request04 cần thêm23665, vượt60000 nên bị chặn trước mạng. | Không biết tổng tokens thực tiêu của hai lỗi. HTTP429/400 không được tự quy thành0 hoặc dùng rate-limit headers làm usage. |

Nguồn evidence gốc giữ nguyên: [HTTP200](../phase3a-live-20261021T070325Z/C01/wire/01/response.json), [HTTP429](../phase3a-live-20261021T070325Z/C01/wire/02/response.json), [HTTP400](../phase3a-live-20261021T070325Z/C01/wire/03/response.json), [request bị chặn](../phase3a-live-20261021T070325Z/C01/blocked-request.json).

Theo tài liệu Groq, header `x-ratelimit-*-requests` nói về **RPD**, còn `*-tokens` nói về **TPM**. Vì thế limit-requests1000/remaining999 không phải bằng chứng RPM còn999. Retry-After chỉ thời gian chờ retry; reset-tokens là thông tin khác. [Groq Rate Limits](https://console.groq.com/docs/rate-limits).

Kiểm tra code và wire receipts không thấy double-retry: runtime chỉ có vòng retry trong `GroqProvider.generate`; httpx transport Phase3A có retries0, chạy tuần tự, một repair sau structural rejection. Ba HTTP thực gửi là draft đầu, repair bị429, retry repair bị400. `llm_calls=4` còn tính cả lượt bị chặn trước transport. Evaluation có hook theo dõi quota và chờ giữa các ca; nó không tự phát sinh HTTP retry.

Groq công bố GPT-OSS120B hỗ trợ strict Structured Outputs; yêu cầu object đóng và các trường required. Native tool use/streaming không được kết hợp với chế độ này; request hiện tại không sử dụng hai tính năng đó. **Giữ nguyên response format và validation**, không chuyển chế độ để né lỗi. Việc tài liệu ghi hỗ trợ không chứng minh request400 chắc chắn có nội dung hợp lệ. [Groq Structured Outputs](https://console.groq.com/docs/structured-outputs).

**2. Bản vá và phạm vi thay đổi**

| File | Thay đổi Phase3B |
|---|---|
| [provider.py](../../backend/landlaw/provider.py) | Nhận optional request budget cho trusted operator; reserve trước từng HTTP, settle cả response lỗi và transport error. HTTP400 format nhận phản hồi sửa định dạng chung thay vì retry cùng instruction; tính chung vào tối đa2 format failures trong một generate. JSON ngoài không hợp lệ/content sai kiểu cũng fail-closed có giới hạn. Ghi counter lỗi cố định, không log error body hoặc hội thoại. |
| [request_budget.py](../../backend/landlaw/request_budget.py) — mới | Ledger durable phân biệt confirmed/estimated/reserved/remaining và quota. Giữ dự phòng nếu crash, thiếu usage hoặc lỗi HTTP; chặn trước mạng khi hết cap. Không tự hoàn dự phòng của429/400. |
| [evaluation.py](../../backend/landlaw/evaluation.py) | Fingerprint gồm module budget mới; hard cap chặn cả suite trước ca tiếp theo, giữ các ca chưa chạy trong mẫu số; ledger đã bị chặn không mở ca khi resume. |
| [evaluate_generation_candidate.py](../../scripts/evaluate_generation_candidate.py) | Gắn ledger vào operator runner; mặc định18requests/60000tokens, giữ qua resume, từ chối âm thầm áp ledger rỗng cho run lịch sử không có accounting. Không thay case/gold. |
| [test_request_budget.py](../../tests/test_request_budget.py) — mới | 30 regression checks cho usage, lỗi429/JSON, retry, giới hạn, persistence và dừng evaluation. |

BudgetExceeded vẫn được import qua `landlaw.provider` để giữ tương thích caller; lớp gốc nằm trong module budget. Public app giữ quota riêng; optional operator ledger không thay quota Groq hoặc quyền truy cập public.

Không sửa synthesis prompt pháp luật, agent graph, source admission, applicability, verifier, số repair, raw source hoặc embedding. Prompt bổ sung chỉ là feedback định dạng chung ở nhánh retry lỗi format. Giữ6LLM requests/12tools/2retrieval rounds/1repair/90giây, max completion2048. Đây là xử lý lỗi có giới hạn, **không phải bằng chứng lỗi JSON provider đã hết trên model thật**.

[Patch chỉ riêng Phase3B](phase3b-only.patch), [bản gốc trước sửa](source-before/), [bằng chứng bảo toàn](preservation.json). Trước sửa,199 file nguồn khớp Phase2D. Sau sửa chỉ3 file cũ ở bảng trên thay đổi, cộng2 file mới; các bản vá F01/F03/Phase2D khác giữ nguyên. Toàn bộ **2.847 file báo cáo lịch sử** được kiểm checksum và không đổi, kể cả S06 và Phase3A.

**3. Token accounting và hard cap**

| Trường | Ý nghĩa | Số kế thừa Phase3A |
|---|---|---:|
| `confirmed_usage` | Tổng `total_tokens` hợp lệ provider trả về | 4.829 |
| `estimated_usage` | Upper bound giữ cho request thiếu usage; không phải lượng thực đo | 47.330 |
| `reserved_budget` | Phần giữ cho request chưa settle, gồm request bị ngắt tiến trình | 0 |
| `remaining_test_budget` | 60000 − confirmed − estimated − reserved | 7.841 |
| Provider quota | Snapshot TPM/RPD/Retry-After, tách khỏi ngân sách test | Không phải số dư ngân sách test |

Reservation vẫn được tính theo **request thực tế**: số byte UTF-8 JSON gửi đi +4096 framing allowance +max completion thực của request. Không dùng một số reservation chung cho mọi payload hoặc tokenizer E5 để đếm GPT-OSS. Hiện chưa chứng minh được upper bound nhỏ hơn cho tokenizer/schema/template phía Groq nên **không giảm dự phòng bằng hệ số phỏng đoán**. Phần4096 là allowance bảo thủ được giữ nguyên, không tuyên bố là số token framing đã đo. Nếu provider báo vượt reservation, ledger ghi số xác nhận và chặn mọi request tiếp theo; đây là vi phạm giả định bound, không có cơ chế tự tiếp tục.

Ledger ghi trước HTTP; response không có usage chuyển reserved sang estimated mà không tăng phần còn lại. Usage có xác nhận mới thay upper bound. Restart giữ request pending; resume giữ cùng identity/caps, kể cả run0requests; lỗi ghi ledger chặn gửi mạng. Sau global cap, không mở ca tiếp theo hoặc tự chạy lại ca lỗi. Ledger được thiết kế cho một operator process tuần tự trên một output; không có khóa liên tiến trình và không được chia sẻ để chạy đồng thời.

[Đối soát allocation cũ](prior-allocation-check.json) đọc receipt có sẵn, dựng ledger mới có provenance và serialize request C02 qua client **không có network I/O**. Không chạy lại ca C01 hoặc model C02. Request đầu C02 là13644bytes, reservation19788, vượt7841 còn lại. [Ledger kế thừa](prior-allocation-ledger.json) giữ hai khoản unknown. Tạo output mới không phải lý do để cấp lại60000 hoặc xóa lịch sử usage; CLI ledger theo output không tự tìm mọi allocation ở thư mục khác, nên operator phải gắn/carry đúng allocation trước khi chạy.

**4. Kết quả tests và preflight**

| Kiểm tra | Kết quả thực tế | Giới hạn |
|---|---|---|
| Backend regression cuối | **516/516 PASS**, trong33.70s | HTTPTransport thật bị chặn; không phải model evaluation |
| Regression mới | **30 PASS** | Success/429/400/invalid JSON/schema/unknown usage/transport error; 6-call runtime và18total; block trước mạng; cap/identity/pending/resume/disk error; suite dừng và giữ mẫu số |
| Frontend unit | **14/14 PASS** | Vitest |
| Frontend build | **PASS** | TypeScript/Vite |
| Playwright | **100/100 PASS** | Desktop/mobile Vite local và API fixtures; không phải public E2E |
| Backend startup | `/healthz`200; database/source gate usable | `/readyz`503 vì cố ý dùng API key rỗng trong test offline; không kiểm provider authentication |
| SQLite backup/restore | PASS: exact documents, thiếu receipt fail-closed, apply lại receipt usable | Không suy tương đương PostgreSQL |
| Source quote fixture | `answered`, mọi citation đã review và có trong synthesis | Trích nguyên văn Điều108; semantic judge là fixture; không phải C02 hoặc model pass |
| Fixture coverage cũ | **9/11 status matches; C02/C03 FAIL** | Không sửa fixture/gold để tăng tỷ lệ đạt |
| PostgreSQL integration | **NOT RUN** | Không có local PostgreSQL/initdb/pg_ctl/psql; Docker WSL integration không hoạt động. Không dùng hai DB URLs remote đang cấu hình |

Logs: [backend cuối](backend-tests-final-2.log), [frontend](frontend-tests.log), [build](frontend-build.log), [Playwright](frontend-e2e.log), [startup/positive fixture](startup-and-positive-fixture-final.json), [coverage fixture](coverage-preflight/report.json), [PostgreSQL](postgres-preflight.json).

Hai fixture cũ bị từ chối vì C02 cite `qd-40-2026-hanoi-9-1-0`, C03 cite `nd-88-2024-0-11-0`, trong khi snapshot thực đã chọn các passage cha tương ứng. Payload C02/C03 giống hệt Phase2D, nên không coi đó là regression mới do sửa API. Tuy nhiên, **vẫn giữ FAIL**, không tự đổi IDs của fixture hoặc cho phép citation ngoài snapshot. Source-quote fixture riêng chỉ kiểm tra luồng phát hành một trích dẫn đúng được review, không thay kết quả hai fixture này.

Trong capture cuối, C02 có **3/3 đoạn bắt buộc,5070 ký tự**; C03 có **7/7,6981 ký tự** và ledger khớp payload thực của bước synthesis. [Synthesis cuối](synthesis-final/report.json). Provider capture cố ý trả `insufficient_evidence` để không tạo đáp án: đó không phải false abstention từ model. Trường legacy `all_three_complete=false` trong report này không áp dụng cho tập đã lọc gồm hai ca positive và ba negative; kết luận dựa trên từng case, không sửa trường đó cho đẹp.

Toàn corpus vẫn59stale/1unknown ở cấp document; scoped receipt policy usable và không xác nhận toàn corpus. Các negative thiếu dữ kiện/ngoài phạm vi/unreviewed giữ từ chối; controls lịch sử vẫn đạt. Không mở nguồn mới. Ngày review hiện hành vẫn21/10/2026, không tự kéo dài đến23/10.

Các lần chạy đầu bị treo asyncio trong sandbox, import script bằng entrypoint chưa đúng, và một assertion trong test mới sai cách so sánh vị trí feedback đã được giữ trong logs. Đã chuyển qua cơ chế quyền thực thi chính thức cho local tests, dùng module entrypoint và sửa assertion test. Không đổi schema hoặc gold để xử lý các lỗi đó. Số PASS trong bảng lấy từ lần cuối sau mọi sửa runtime. Sau chỉnh import trong test mới, chạy lại30/30 regression đạt; lint hai file mới PASS. [Log30tests](accounting-tests-after-import-check.log), [lint](lint-new-files.log).

**5. Retrieval Recall@5 offline trên cấu hình cuối**

| Phân nhóm | Mẫu số câu có gold | Macro Recall@5 |
|---|---:|---:|
| Smoke | 10 | 100% |
| Supplemental | 3 | 100% |
| Natural | 6 | 91,67% |
| Tổng | **19** | **97,37%** |

**Micro Recall@5 =20/21 gold chunks =95,24%.** S06 được loại trước chạy theo yêu cầu;12 câu không có gold positive không thuộc mẫu số Recall. Không loại N03 đạt0,5: thiếu gold parent `luat-dat-dai-2024-107-1-parent` trong top5, dù child liên quan xuất hiện. Không đổi gold hoặc tính parent/child tương đương để tăng điểm.

Backend đo là **SQLite tách biệt**, corpus v5, E5 đúng checksum, query gốc theo ngày hỏi và history giữ trong dataset nhưng không rewrite query. Đây là raw hybrid retrieval có cơ chế candidate replacement hiện có, không agent expansion, không answer correctness. Chỉ số admission trên cùng top5 không refill cũng97,37%; không chứng minh mọi nguồn hay mọi ngày đều fresh. [Kết quả và mẫu số từng câu](retrieval-final/retrieval-recall-at5.json). Các metrics model/faithfulness/citation accuracy/answer correctness/latency model không chạy hoặc suy ra từ Recall.

**6. Release candidate identity**

- HEAD: `117e7bd2c4a320c3d02256dfdabf858180b47dbf`; working tree dirty có chủ đích, chưa có candidate commit.
- Source-tree SHA256: `4a7a61b0c3d464bd142ab8887cbaca377f449c66609ef653088a3023734e5a66` —201 file nguồn.
- Runtime SQLite fingerprint: `1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d`.
- Candidate identity: `58302e9117ccc44c926a71a20dc06eb088e9f45ef64f98b65654d2b716bb3e61`.
- Corpus payload SHA256 giữ nguyên: `7ce7956ae35c7006b5bfd7d10d516fa9e8e47fe2f073e471ceecbb34b412d317`.

[Manifest mới](release-manifest.json) gắn checksum corpus, receipt bundle, source policy và cả ba suite khóa; [source hashes](source-files-sha256.json). Capture/retrieval/startup cuối cùng cùng fingerprint trên. Báo cáo giữa vòng ở fingerprint80512… được giữ, không sửa thành cấu hình cuối. Fingerprint PostgreSQL trong manifest chỉ là **planned**, chưa được xác nhận qua database thật. Model,384chiều embedding và mọi gold giữ nguyên.

**7. Blockers và pilot tối thiểu tiếp theo để review**

1. Allocation cũ không đủ reservation cho C02; không tự refund unknown errors hoặc nâng cap. Muốn tiếp tục trong cùng60000 cần có bằng chứng usage/bound hợp lệ để đối soát hai request lỗi; không suy từ quota headers hoặc failed_generation. Không tự thực hiện tra cứu tài khoản/provider trong vòng này.
2. JSON provider400 chưa có root cause chi tiết và bản vá chưa được đo bằng model thật. Không hứa lỗi đã biến mất.
3. C01 chưa đạt answer correctness, S06 vẫn FAIL; C02/C03 chưa có model pass. Hai fixture cũ còn FAIL được ghi nhận ở trên.
4. Chưa có PostgreSQL integration, role/migration/restore trên PG, deployed fingerprint hoặc public E2E của candidate này. Scope pháp luật ngày23/10 chưa được review.

Pilot tối thiểu đề xuất: **chỉ C02**, một attempt, câu hỏi/as_of/legal scope giữ đúng file Phase2C, SQLite riêng; dùng Groq/model hiện tại, tối đa6HTTP requests gồm retry/repair,90giây và hard cap60000 không đổi, không judge ngoài pipeline. Gắn ledger đúng allocation trước khi chạy; không tự cấp lại60000 cho output mới. Nếu vẫn dùng allocation hiện tại, preflight phải chặn trước API như phép kiểm ở trên.

Khi và chỉ khi ngân sách hợp lệ đã được review và người dùng cho phép model, dùng một harness C02 mới gắn `GroqProvider(request_budget=...)`, khóa manifest/fingerprint, capture request thực/visible response/usage/verdict và giữ mọi attempt. C02 không thuộc suite20+4+8 nên không chèn case vào gold hoặc truyền `--case-id C02` cho frozen-suite CLI. Không chạy lại C01/S06, không chạy C03/full evaluation để thử vận may. Hễ quota/timeout/budget chặn thì ghi INCOMPLETE và dừng.

**Quyết định: NOT READY trong allocation hiện có; không tự chuyển sang model pilot hoặc release validation. Dừng Phase3B để review, không tiếp tục sửa runtime.**

Secret scan PASS; `git diff --check` PASS. [Secret scan](secrets-check-final.log), [chỉ mục artifact/checksum](artifact-sha256.json).
