# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> answered composer is compact and does not cover the end of the answer
- Location: e2e/navigation.spec.ts:77:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.message.assistant').last()
Expected: visible
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('.message.assistant').last() with timeout 5000ms
  - waiting for locator('.message.assistant').last()
  - Test timeout of 30000ms exceeded.

```

```yaml
- link "Đến nội dung chính":
  - /url: "#main-content"
- complementary "Thanh điều hướng":
  - link "Vành đai 4":
    - /url: "#"
  - button "Đóng menu":
    - img
  - button "Cuộc trò chuyện mới" [disabled]:
    - img
    - text: Cuộc trò chuyện mới
  - navigation "Điều hướng chính":
    - button "Hỏi đáp pháp luật":
      - img
      - text: Hỏi đáp pháp luật
    - button "Thư viện văn bản":
      - img
      - text: Thư viện văn bản
    - button "Đánh giá hệ thống":
      - img
      - text: Đánh giá hệ thống
  - text: Lịch sử trên thiết bị
  - button "Câu hỏi kiểm thử" [disabled]
  - button "Xóa cuộc trò chuyện Câu hỏi kiểm thử" [disabled]:
    - img
  - button "Thông tin dữ liệu và kết nối":
    - img
    - text: Dữ liệu và kết nối
  - button "Đổi giao diện sáng tối":
    - img
    - text: Giao diện tối
  - button "Xóa toàn bộ lịch sử" [disabled]:
    - img
    - text: Xóa toàn bộ lịch sử
  - paragraph: Lưu tại máy trong 7 ngày. Không đồng bộ giữa thiết bị.
- main:
  - button "Mở menu điều hướng":
    - img
  - text: Vành đai 4
  - button "Thông tin dữ liệu và kết nối":
    - img
  - button "Cuộc trò chuyện mới" [disabled]:
    - img
  - article:
    - paragraph: Câu hỏi kiểm thử
  - status:
    - img
    - text: Đang kết nối và chuẩn bị tra cứu…
    - button "Xem quá trình"
  - status:
    - paragraph: Đang kết nối dịch vụ. Lần khởi động đầu có thể mất khoảng một phút…
    - button "Kiểm tra kết nối" [disabled]
  - textbox "Câu hỏi pháp luật":
    - /placeholder: Nhập câu hỏi pháp luật…
  - text: Chỉ nhập tình huống đã ẩn danh
  - button "Dừng lượt hỏi":
    - img
  - paragraph: Có thể có sai sót. Hãy kiểm tra nguồn trước khi áp dụng.
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test'
  2   | 
  3   | test.beforeEach(async ({ page }) => {
  4   |   await page.route('**/api/v1/status', r => r.fulfill({ json: { generation_available: true, reason: null } }))
  5   |   // Only test fixtures use intercepted APIs. Production never registers these responses.
  6   |   await page.route('**/readyz', r => r.fulfill({ status: 503, json: { status: 'not_ready', database: true, llm_configured: true } }))
  7   |   await page.route('**/api/v1/documents', r => r.fulfill({ json: { documents: [] } }))
  8   |   await page.route('**/api/v1/projects', r => r.fulfill({ json: { projects: [] } }))
  9   |   await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: { status: 'not_run', results: [] } }))
  10  | })
  11  | 
  12  | test('responsive navigation honestly shows unpublished corpus and benchmark', async ({ page }, info) => {
  13  |   const errors: string[] = []
  14  |   page.on('pageerror', e => errors.push(e.message))
  15  |   await page.goto('/')
  16  |   await expect(page.getByRole('heading', { name: /Bạn đang vướng việc gì/ })).toBeVisible()
  17  |   await expect(page.getByLabel('Câu hỏi pháp luật')).toBeVisible()
  18  |   await expect(page.getByLabel('Dự án', { exact: true })).toHaveCount(0)
  19  |   await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeDisabled()
  20  |   await page.screenshot({ path: info.outputPath(`ui-${info.project.name}.png`), fullPage: true })
  21  |   expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  22  |   if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  23  |   await page.getByRole('button', { name: 'Thư viện văn bản', exact: true }).click()
  24  |   await expect(page.getByRole('heading', { name: 'Corpus chưa được công bố' })).toBeVisible()
  25  |   if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  26  |   await page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true }).click()
  27  |   await expect(page.getByRole('heading', { name: 'Chưa có kết quả kiểm tra trên bản này' })).toBeVisible()
  28  |   expect(errors).toEqual([])
  29  | })
  30  | 
  31  | test('technical demo clearly discloses pending legal acceptance and coverage gaps', async ({ page }) => {
  32  |   await page.route('**/readyz', r => r.fulfill({ json: {status:'ready',database:true,llm_configured:true,
  33  |     corpus_release:'reviewed-test-corpus',publication_profile:'technical_demo',quality_status:'acceptance_pending',
  34  |     checked_at:'2026-10-13T00:00:00Z',coverage_gaps:[{document_id:'missing',title:'Nguồn còn thiếu',reason:'Chưa có toàn văn đạt kiểm tra.'}]}}))
  35  |   await page.goto('/')
  36  |   if(await page.getByRole('button',{name:'Mở menu điều hướng'}).isVisible()) await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
  37  |   await page.getByRole('button', { name: 'Thông tin dữ liệu và kết nối' }).filter({visible:true}).click()
  38  |   await expect(page.getByRole('note')).toContainText('Bản thử nghiệm — chưa được thẩm định pháp lý độc lập.')
  39  |   await page.getByText('Các nguồn chưa đủ dữ liệu (1)').click()
  40  |   await expect(page.getByRole('dialog')).toContainText('Nguồn còn thiếu: Chưa có toàn văn đạt kiểm tra.')
  41  | })
  42  | 
  43  | test('API quota errors are displayed without an invented answer', async ({ page }) => {
  44  |   await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'test-session', token: 'test-session-token' } }))
  45  |   await page.route('**/api/v1/chat', r => r.fulfill({ status: 429, headers: { 'Retry-After': '37' }, json: { detail: 'limited' } }))
  46  |   await page.goto('/')
  47  |   await page.getByLabel('Câu hỏi pháp luật').fill('Cần kiểm tra điều kiện bồi thường nào?')
  48  |   await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  49  |   await expect(page.getByRole('alert')).toContainText('37 giây')
  50  |   await expect(page.locator('.message.assistant')).toHaveCount(0)
  51  | })
  52  | 
  53  | test('verified SSE answer opens source and trace with keyboard dismissal', async ({ page }) => {
  54  |   const citation = { id: 'law-article', document_id: 'law', title: 'Nguồn thử nghiệm giao diện', document_number: '40/2026/QĐ-UBND', url: 'https://hanoi.gov.vn/', locator: 'Điều 29', excerpt: 'Trích đoạn kiểm thử, không phải dữ liệu pháp lý.', checked_at: '2026-10-11T00:00:00Z', applicability: 'current', page: 6, source_url: 'https://datafiles.hanoi.gov.vn/test-fixture.pdf#page=6' }
  55  |   const trace = [{ step: 'verify', tool: 'check_effectivity', summary: 'Đã kiểm tra nguồn trong fixture.', document_ids: ['law'], elapsed_ms: 50 }]
  56  |   const result = { status: 'clarification_needed', content: 'Cần bổ sung thời điểm quyết định.', citations: [citation], trace, trace_id: 'ui-test-trace', elapsed_ms: 100, tool_calls: 1 }
  57  |   await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'test-session', token: 'test-session-token' } }))
  58  |   await page.route('**/api/v1/chat', r => r.fulfill({ contentType: 'text/event-stream', body: `event: progress\ndata: ${JSON.stringify(trace[0])}\n\nevent: result\ndata: ${JSON.stringify(result)}\n\n` }))
  59  |   await page.goto('/')
  60  |   await page.getByLabel('Câu hỏi pháp luật').fill('Một câu hỏi kiểm thử giao diện')
  61  |   await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  62  |   await expect(page.locator('.message.assistant')).toContainText(result.content)
  63  |   await page.getByRole('button', { name: /40\/2026/ }).click()
  64  |   await expect(page.locator('[aria-label="Nguồn căn cứ"]')).toContainText(citation.excerpt)
  65  |   await expect(page.getByRole('link', { name: 'Mở nguồn chính thức' })).toHaveAttribute('href', citation.url)
  66  |   await expect(page.getByRole('link', { name: 'Mở trang nguồn gốc' })).toHaveAttribute('href', citation.source_url)
  67  |   await expect(page.locator('[aria-label="Nguồn căn cứ"]')).toContainText('Trang nguồn: 6')
  68  |   await page.keyboard.press('Escape')
  69  |   await expect(page.getByRole('dialog')).toHaveCount(0)
  70  |   await page.getByRole('button', { name: /Xem quá trình kiểm chứng/ }).click()
  71  |   await expect(page.getByRole('dialog', { name: 'Quá trình kiểm chứng' })).toContainText(trace[0].summary)
  72  |   await page.keyboard.press('Escape')
  73  |   await expect(page.getByRole('dialog')).toHaveCount(0)
  74  | })
  75  | 
  76  | 
  77  | test('answered composer is compact and does not cover the end of the answer', async ({page}) => {
  78  |   await page.route('**/readyz', r=>r.fulfill({json:{status:'ready'}}))
  79  |   await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'compact',token:'fixture'}}))
  80  |   await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: '+JSON.stringify({trace_id:'compact',status:'answered',content:'Câu trả lời kiểm thử. '.repeat(100),citations:[],trace:[],tool_calls:1,elapsed_ms:50})+'\n\n'}))
  81  |   for(const width of [1440,390,320]) {
  82  |     await page.setViewportSize({width,height:667})
  83  |     await page.goto('/')
  84  |     await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi kiểm thử')
  85  |     await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
> 86  |     await expect(page.locator('.message.assistant').last()).toBeVisible()
      |                                                             ^ Error: expect(locator).toBeVisible() failed
  87  |     const composer=await page.locator('.composer').boundingBox()
  88  |     expect(composer!.height).toBeLessThanOrEqual(120)
  89  |     expect(composer!.height).toBeGreaterThanOrEqual(80)
  90  |     await page.locator('.chat-scroll').evaluate(el=>{el.scrollTop=el.scrollHeight})
  91  |     const end=await page.locator('.message.assistant .trace-link').last().boundingBox()
  92  |     expect(end!.y+end!.height).toBeLessThanOrEqual(composer!.y)
  93  |     expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  94  |     await page.evaluate(()=>{sessionStorage.clear();return new Promise<void>((resolve,reject)=>{const r=indexedDB.deleteDatabase('landlaw-history');r.onsuccess=()=>resolve();r.onerror=()=>reject(r.error)})})
  95  |   }
  96  | })
  97  | 
  98  | test('evaluation separates answer quality from refusals and labels absent citations', async ({ page }) => {
  99  |   await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: {
  100 |     status: 'reviewed', matches_active_release: true, matches_active_configuration: true, model: 'fixture-model',
  101 |     results: [{ pass: 1, partial: 0, fail: 1 }],
  102 |     supplemental: {cases:4,completed:4,pass:0,partial:1,fail:3,execution_failures:2,note:'Câu hỏi tự nhiên được kiểm tra riêng; không gộp vào suite chính.'},
  103 |     limitations: ['Verifier có thể bỏ sót diễn giải sai.'],
  104 |     metrics: { groups: {
  105 |       answered: { cases: 1, pass: 0, partial: 0, fail: 1 },
  106 |       insufficient: { cases: 1, pass: 1, partial: 0, fail: 0 },
  107 |     }, answer_origin: { llm: 1, deterministic: 1, unknown: 0 } },
  108 |     case_results: [{ id: 'fixture-refusal', status: 'insufficient_evidence', review: 'pass', seconds: 0.1,
  109 |       citations_valid: null, note: 'Thông báo ngoài phạm vi trong fixture.' }],
  110 |   } }))
  111 |   await page.goto('/')
  112 |   if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  113 |   await page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true }).click()
  114 |   await expect(page.getByText('Trả lời nội dung', { exact: true })).toBeVisible()
  115 |   await expect(page.locator('.eval-behavior').getByText('Thiếu chứng cứ / ngoài phạm vi', { exact: true })).toBeVisible()
  116 |   await page.locator('.eval-case summary').filter({hasText:'fixture-refusal'}).click()
  117 |   await expect(page.getByText('Không áp dụng', { exact: true })).toBeVisible()
  118 |   await expect(page.locator('.eval-card-eyebrow').filter({hasText:'Bổ sung'})).toBeVisible()
  119 |   await expect(page.getByText('Verifier có thể bỏ sót diễn giải sai.', { exact: true })).toBeVisible()
  120 |   await expect(page.getByText(/không phải độ chính xác trả lời pháp luật/)).toBeVisible()
  121 | })
  122 | 
```