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
  await expect(page.getByRole('heading', { name: /Hiểu rõ pháp luật/ })).toBeVisible()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeVisible()
  await expect(page.getByLabel('Dự án', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeDisabled()
  await page.screenshot({ path: `../reports/ui-${info.project.name}.png`, fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.getByRole('button', { name: 'Thư viện văn bản', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Corpus chưa được công bố' })).toBeVisible()
  await page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Chưa có kết quả benchmark' })).toBeVisible()
  expect(errors).toEqual([])
})

test('technical demo clearly discloses pending legal acceptance and coverage gaps', async ({ page }) => {
  await page.route('**/readyz', r => r.fulfill({ json: {status:'ready',database:true,llm_configured:true,
    corpus_release:'reviewed-test-corpus',publication_profile:'technical_demo',quality_status:'acceptance_pending',
    checked_at:'2026-10-13T00:00:00Z',coverage_gaps:[{document_id:'missing',title:'Nguồn còn thiếu',reason:'Chưa có toàn văn đạt kiểm tra.'}]}}))
  await page.goto('/')
  await expect(page.getByRole('note')).toContainText('Demo kỹ thuật — chưa nghiệm thu pháp lý.')
  await page.getByText('Các nguồn chưa đủ dữ liệu (1)').click()
  await expect(page.getByRole('note')).toContainText('Nguồn còn thiếu: Chưa có toàn văn đạt kiểm tra.')
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
  await expect(page.getByRole('dialog', { name: 'Chi tiết nguồn' })).toContainText(citation.excerpt)
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
