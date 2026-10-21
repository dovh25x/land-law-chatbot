# Evidence index

Index liên kết artifact gốc, không sao chép benchmark hoặc sửa receipt lịch sử. SHA-256 các file được trích dẫn nằm trong [evidence-index.json](evidence-index.json); tất cả 2.906 file lịch sử trước Phase 4 nằm trong [baseline](baseline.json). [Validation](validation.json) kiểm core/history và các link; [freeze manifest](freeze-manifest.json) xác định candidate. Một link tồn tại hoặc một hash khớp không tự chứng minh nội dung pháp lý đúng.

### E01

**Candidate identity/corpus/receipts.** [Phase3B release manifest](../../phase3b-reliability-20261021T073924Z/release-manifest.json), [source hashes](../../phase3b-reliability-20261021T073924Z/source-files-sha256.json), [completion](../../phase3b-reliability-20261021T073924Z/completion.json), [candidate corpus asset](../../../data/staging/phase2c-current/release-v5.json), [policy](../../phase2c-current-20261021/source-gate-final.json), [receipt folder](../../phase2c-current-20261021/receipts-final/). Corpus asset bị gitignore; checksum không thay việc giao asset. Không sửa manifests cũ khi có `.dockerignore` mới.

### E02

**Provider/accounting.** [Phase3B report](../../phase3b-reliability-20261021T073924Z/README.md), [prior allocation](../../phase3b-reliability-20261021T073924Z/prior-allocation-check.json), [ledger](../../phase3b-reliability-20261021T073924Z/prior-allocation-ledger.json), [30tests](../../phase3b-reliability-20261021T073924Z/accounting-tests-after-import-check.log), [budget module](../../../backend/landlaw/request_budget.py), [provider](../../../backend/landlaw/provider.py), [runner](../../../scripts/evaluate_generation_candidate.py). Unknown usage không phải confirmed spend; quota provider khác budget nội bộ.

### E03

**Retrieval SQLite final.** [Receipt/từng câu](../../phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json), [script offline](../../phase3b-reliability-20261021T073924Z/retrieval-final/offline_retrieval.py), [smoke](../../../data/evaluation/smoke.jsonl), [supplemental](../../../data/evaluation/supplemental.jsonl), [natural](../../../data/evaluation/natural.jsonl). 19 eligible,20/21 hits; macro 97,37%,micro 95,24%; không all 32/current/model answer score.

### E04

**Fixture/restore.** [Final startup/quote fixture](../../phase3b-reliability-20261021T073924Z/startup-and-positive-fixture-final.json), [harness](../../phase3b-reliability-20261021T073924Z/offline_positive_startup_final.py), [coverage11case trung gian](../../phase3b-reliability-20261021T073924Z/coverage-preflight/report.json). Final quote FP 1697…;9/11 fixture FP 8051…; không trộn cohort. Ready 503 do cố ý không key không phải public outage.

### E05

**Legal review và scope.** [LEGAL_REVIEW](../../phase2c-current-20261021/LEGAL_REVIEW.md), [case khóa](../../phase2c-current-20261021/acceptance-cases-final.json), [policy](../../phase2c-current-20261021/source-gate-final.json), [receipts](../../phase2c-current-20261021/receipts-final/), [legal relations](../../../data/legal_relations.json). URL nguồn chính thức, quan hệ sửa đổi/chuyển tiếp và ngày review nằm ở biên bản gốc; không xác nhận fresh mọi văn bản hoặc ngày 23/10.

### E06

**Actual synthesis capture.** [Phase2D acceptance](../../phase2d-synthesis-20261021/acceptance-locked/report.json), [Phase2D manifest](../../phase2d-synthesis-20261021/release-manifest.json), [final C02/C03 capture](../../phase3b-reliability-20261021T073924Z/synthesis-final/report.json), [capture script](../../../scripts/verify_synthesis_integrity.py), [synthesis code](../../../backend/landlaw/synthesis_context.py), [regression](../../../tests/test_synthesis_integrity.py). Completeness không thay model correctness.

### E07

**Phase 3A model pilot thất bại/dở dang.** [Execution](../../phase3a-live-20261021T070325Z/execution.json), [C01 attempt](../../phase3a-live-20261021T070325Z/C01/attempt.json), [technical review](../../phase3a-live-20261021T070325Z/technical-review.json), [configuration lock](../../phase3a-live-20261021T070325Z/configuration-lock.json). Fingerprint 37 d 2…; raw C02/C03 placeholders không phải attempt. Không sửa response/JSON lỗi hoặc bịa failed_generation đã không lưu.

### E08

**Failures và faithfulness lịch sử.** [S06 final technical review](../../phase1-s06-final-20261020T161058Z-b031ce/technical-review.json), [S06 final folder](../../phase1-s06-final-20261020T161058Z-b031ce/), [S06 attempt trước](../../phase1-s06-20261020T154327Z-7fa717/), [customfaithfulness c4f0…](../../evaluation/ring4-c4f0c661/faithfulness.json), [customfaithfulness800c…](../../evaluation/ring4-800c96ba/faithfulness.json), [historical evaluation folders](../../evaluation/). Giữ FAIL và null; không gộp fingerprints, không gọi custom evaluator là RAGAS.

### E09

**Yêu cầu sản phẩm.** [PRD](../../../docs/PRD.md), [README](../../../README.md), [docs index](../../../docs/README.md), [AGENTS](../../../AGENTS.md). Chưa có syllabus/rubric trong repo; không dùng PRD thay chứng nhận học phần.

### E10

**Architecture.** [Architecture](../../../docs/ARCHITECTURE.md), [diagram SVG](../../../docs/diagrams/architecture.svg), [HTML source](../../../docs/diagrams/architecture.html), [pinned diagram workflow](../../../docs/diagrams/README.md). Tái sử dụng diagram-design asset; không tạo Mermaid hoặc sơ đồ pipeline khác.

### E11

**Technology decisions.** [ADR index](../../../docs/adr/README.md), [pyproject](../../../pyproject.toml), [requirements.lock](../../../requirements.lock), [frontend package](../../../frontend/package.json), [frontend lock](../../../frontend/package-lock.json). LangGraph/Groq là quyết định triển khai; không có benchmark framework superiority.

### E12

**Embedding/retrieval contract.** [Local embedding implementation](../../../backend/landlaw/local_embedding.py), [contract](../../../backend/landlaw/embedding.py), [retrieval](../../../backend/landlaw/retrieval.py), [Store search](../../../backend/landlaw/store.py), [offline worker](../../../scripts/offline_e5_colab.py). SQLite lexical/dot product khác PG fulltext/vector; không gọi tất cả là BM 25.

### E13

**F01/F03 guards.** [Agent](../../../backend/landlaw/agent.py), [source review regression](../../../tests/test_source_review_policy.py), [scoped gate regression](../../../tests/test_scoped_source_gate.py), [clause dependency](../../../tests/test_clause_dependencies.py), [OR/AND](../../../tests/test_alternative_condition_logic.py). Unit pass không đổi S06 FAIL hoặc thay independent legal review.

### E14

**Frontend/privacy/API.** [Handoff](../../../docs/FRONTEND.md), [API](../../../docs/API.md), [frontend source](../../../frontend/src/), [Phase3B unit log](../../phase3b-reliability-20261021T073924Z/frontend-tests.log), [build log](../../phase3b-reliability-20261021T073924Z/frontend-build.log), [Playwright log](../../phase3b-reliability-20261021T073924Z/frontend-e2e.log). 100 browser tests là local fixtures; chưa public.

### E15

**PostgreSQL/restore.** [Migrations](../../../migrations/), [migration006](../../../migrations/006_browser_history.sql), [Phase3B PG NOT RUN](../../phase3b-reliability-20261021T073924Z/postgres-preflight.json), [Phase4 PG actual receipt](postgres-preflight.json), [Phase4 harness](postgres_preflight.py). Phase 4 được phép bổ sung Docker local; không đổi kết quả NOT RUN lịch sử, không remote/production.

### E16

**Release/packaging.** [Operations](../../../docs/OPERATIONS.md), [Dockerfile](../../../Dockerfile), [.dockerignore](../../../.dockerignore), [CI](../../../.github/workflows/ci.yml), [deploy workflow](../../../.github/workflows/deploy.yml), [release packager](../../../scripts/package_release.py), [dependency lock check](dependency-lock-check.json), [packaging check](packaging-check.json), [Docker receipt](docker-preflight.json). Local image không phải deployed image hay CI result.

### E17

**Software tests và kiểm cuối.** [516tests Phase3B](../../phase3b-reliability-20261021T073924Z/backend-tests-final-2.log), [Phase4 Python3.12 lần đầu](backend-python312-docker.log), [Python3.12 testtools](backend-python312-testtools.log), [memory](docker-memory-check.log), [validation](validation.json), [secret scan](secrets-check.log), [pip check](pip-check.log). Mọi lần fail được giữ và phân loại; không cộng các lần chạy thành số test độc lập.
