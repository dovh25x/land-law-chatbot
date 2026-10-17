import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  // Only test fixtures use intercepted APIs. Production never registers these responses.
  await page.route('**/readyz', r => r.fulfill({ status: 503, json: { status: 'not_ready', database: true, llm_configured: true } }))
  await page.route('**/api/v1/documents', r => r.fulfill({ json: { documents: [] } }))
  await page.route('**/api/v1/projects', r => r.fulfill({ json: { projects: [] } }))
  await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: { status: 'not_run', results: [] } }))
})

test('responsive navigation honestly shows unpublished corpus and benchmark', async ({ page }, info) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Bạn muốn tìm hiểu điều gì/ })).toBeVisible()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeVisible()
  await expect(page.getByLabel('Dự án', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeDisabled()
  await page.screenshot({ path: `../reports/ui-${info.project.name}.png`, fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  await page.getByRole('button', { name: 'Thư viện văn bản', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Corpus chưa được công bố' })).toBeVisible()
  if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  await page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Chưa có kết quả kiểm tra trên bản này' })).toBeVisible()
  expect(errors).toEqual([])
})

test('technical demo clearly discloses pending legal acceptance and coverage gaps', async ({ page }) => {
  await page.route('**/readyz', r => r.fulfill({ json: {status:'ready',database:true,llm_configured:true,
    corpus_release:'reviewed-test-corpus',publication_profile:'technical_demo',quality_status:'acceptance_pending',
    checked_at:'2026-10-13T00:00:00Z',coverage_gaps:[{document_id:'missing',title:'Nguồn còn thiếu',reason:'Chưa có toàn văn đạt kiểm tra.'}]}}))
  await page.goto('/')
  if(await page.getByRole('button',{name:'Mở menu điều hướng'}).isVisible()) await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
  await page.getByRole('button', { name: 'Thông tin dữ liệu và kết nối' }).filter({visible:true}).click()
  await expect(page.getByRole('note')).toContainText('Bản thử nghiệm — chưa được thẩm định pháp lý độc lập.')
  await page.getByText('Các nguồn chưa đủ dữ liệu (1)').click()
  await expect(page.getByRole('dialog')).toContainText('Nguồn còn thiếu: Chưa có toàn văn đạt kiểm tra.')
})

test('API quota errors are displayed without an invented answer', async ({ page }) => {
  await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'test-session', token: 'test-session-token' } }))
  await page.route('**/api/v1/chat', r => r.fulfill({ status: 429, headers: { 'Retry-After': '37' }, json: { detail: 'limited' } }))
  await page.goto('/')
  await page.getByLabel('Câu hỏi pháp luật').fill('Cần kiểm tra điều kiện bồi thường nào?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.getByRole('alert')).toContainText('37 giây')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
})

test('verified SSE answer opens source and trace with keyboard dismissal', async ({ page }) => {
  const citation = { id: 'law-article', document_id: 'law', title: 'Nguồn thử nghiệm giao diện', document_number: '40/2026/QĐ-UBND', url: 'https://hanoi.gov.vn/', locator: 'Điều 29', excerpt: 'Trích đoạn kiểm thử, không phải dữ liệu pháp lý.', checked_at: '2026-10-11T00:00:00Z', applicability: 'current', page: 6, source_url: 'https://datafiles.hanoi.gov.vn/test-fixture.pdf#page=6' }
  const trace = [{ step: 'verify', tool: 'check_effectivity', summary: 'Đã kiểm tra nguồn trong fixture.', document_ids: ['law'], elapsed_ms: 50 }]
  const result = { status: 'clarification_needed', content: 'Cần bổ sung thời điểm quyết định.', citations: [citation], trace, trace_id: 'ui-test-trace', elapsed_ms: 100, tool_calls: 1 }
  await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'test-session', token: 'test-session-token' } }))
  await page.route('**/api/v1/chat', r => r.fulfill({ contentType: 'text/event-stream', body: `event: progress\ndata: ${JSON.stringify(trace[0])}\n\nevent: result\ndata: ${JSON.stringify(result)}\n\n` }))
  await page.goto('/')
  await page.getByLabel('Câu hỏi pháp luật').fill('Một câu hỏi kiểm thử giao diện')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant')).toContainText(result.content)
  await page.getByRole('button', { name: /40\/2026/ }).click()
  await expect(page.getByRole('dialog', { name: 'Nguồn căn cứ' })).toContainText(citation.excerpt)
  await expect(page.getByRole('link', { name: 'Mở nguồn chính thức' })).toHaveAttribute('href', citation.url)
  await expect(page.getByRole('link', { name: 'Mở trang PDF gốc' })).toHaveAttribute('href', citation.source_url)
  await expect(page.getByRole('dialog')).toContainText('Trang nguồn: 6')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: /Xem quá trình kiểm chứng/ }).click()
  await expect(page.getByRole('dialog', { name: 'Quá trình kiểm chứng' })).toContainText(trace[0].summary)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})


test('answered composer is compact and does not cover the end of the answer', async ({page}) => {
  await page.route('**/readyz', r=>r.fulfill({json:{status:'ready'}}))
  await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'compact',token:'fixture'}}))
  await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: '+JSON.stringify({trace_id:'compact',status:'answered',content:'Câu trả lời kiểm thử. '.repeat(100),citations:[],trace:[],tool_calls:1,elapsed_ms:50})+'\n\n'}))
  for(const width of [1440,390,320]) {
    await page.setViewportSize({width,height:667})
    await page.goto('/')
    await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi kiểm thử')
    await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
    await expect(page.locator('.message.assistant').last()).toBeVisible()
    const composer=await page.locator('.composer').boundingBox()
    expect(composer!.height).toBeLessThanOrEqual(120)
    expect(composer!.height).toBeGreaterThanOrEqual(80)
    await page.locator('.chat-scroll').evaluate(el=>{el.scrollTop=el.scrollHeight})
    const end=await page.locator('.message.assistant .trace-link').last().boundingBox()
    expect(end!.y+end!.height).toBeLessThanOrEqual(composer!.y)
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
    await page.evaluate(()=>{sessionStorage.clear();return new Promise<void>((resolve,reject)=>{const r=indexedDB.deleteDatabase('landlaw-history');r.onsuccess=()=>resolve();r.onerror=()=>reject(r.error)})})
  }
})

test('evaluation separates answer quality from refusals and labels absent citations', async ({ page }) => {
  await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: {
    status: 'reviewed', matches_active_release: true, matches_active_configuration: true, model: 'fixture-model',
    results: [{ pass: 1, partial: 0, fail: 1 }],
    supplemental: {cases:4,completed:4,pass:0,partial:1,fail:3,execution_failures:2,note:'Câu hỏi tự nhiên được kiểm tra riêng; không gộp vào suite chính.'},
    limitations: ['Verifier có thể bỏ sót diễn giải sai.'],
    metrics: { groups: {
      answered: { cases: 1, pass: 0, partial: 0, fail: 1 },
      insufficient: { cases: 1, pass: 1, partial: 0, fail: 0 },
    }, answer_origin: { llm: 1, deterministic: 1, unknown: 0 } },
    case_results: [{ id: 'fixture-refusal', status: 'insufficient_evidence', review: 'pass', seconds: 0.1,
      citations_valid: null, note: 'Thông báo ngoài phạm vi trong fixture.' }],
  } }))
  await page.goto('/')
  if (await page.getByRole('button', { name: 'Mở menu điều hướng' }).isVisible()) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  await page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true }).click()
  await expect(page.getByText('Trả lời nội dung', { exact: true })).toBeVisible()
  await expect(page.getByText('Thiếu chứng cứ / ngoài phạm vi', { exact: true })).toBeVisible()
  await expect(page.getByText('Không áp dụng', { exact: true })).toBeVisible()
  await expect(page.getByText('Kiểm tra bổ sung', { exact: true })).toBeVisible()
  await expect(page.getByText('Verifier có thể bỏ sót diễn giải sai.', { exact: true })).toBeVisible()
  await expect(page.getByText(/không phải độ chính xác trả lời pháp luật/)).toBeVisible()
})
