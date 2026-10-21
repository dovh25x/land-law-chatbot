import { test, expect, type Page } from '@playwright/test'

const citation = {
  id: 'law-article',
  document_id: 'law',
  title: 'Quy định về bồi thường',
  document_number: '40/2026/QĐ-UBND',
  url: 'https://hanoi.gov.vn/',
  locator: 'Điều 29',
  excerpt: 'Người sử dụng đất có giấy chứng nhận được xem xét bồi thường theo điều kiện luật định.',
  checked_at: '2026-10-11T00:00:00Z',
  applicability: 'current',
  source_url: 'https://datafiles.hanoi.gov.vn/test-fixture.pdf#page=6',
  page: 6,
}

const answer = (text: string) => ({
  status: 'answered',
  content: text,
  citations: [citation],
  trace: [],
  trace_id: 'simple-rag-fixture',
  mode: 'simple_rag',
  model: 'fixture',
  llm_calls: 1,
})

async function send(page: Page, message: string) {
  await page.getByLabel('Câu hỏi pháp luật').fill(message)
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
}

test.beforeEach(async ({ page }) => {
  await page.route('**/readyz', route => route.fulfill({ json: { status: 'ready', database: true, llm_configured: true } }))
  await page.route('**/api/v1/status', route => route.fulfill({ json: { generation_available: true, reason: null } }))
  await page.route('**/api/v1/documents', route => route.fulfill({ json: { documents: [], references: [] } }))
  await page.route('**/api/v1/sessions', route => route.fulfill({ status: 201, json: { session_id: 'simple-rag', token: 'fixture-token' } }))
})

test('answers a legal question with Markdown and a source panel', async ({ page }) => {
  const requests: Record<string, unknown>[] = []
  await page.route('**/api/v1/chat', route => {
    requests.push(route.request().postDataJSON() as Record<string, unknown>)
    return route.fulfill({
      contentType: 'text/event-stream',
      body: `event: result\ndata: ${JSON.stringify(answer('## Điều kiện chung\\n\\nBạn có thể được xem xét bồi thường theo hồ sơ [S1].'))}\n\n`,
    })
  })
  await page.goto('/')
  await send(page, 'Nhà tôi có sổ đỏ thì có được bồi thường không?')
  await expect(page.locator('.message.assistant')).toContainText('Điều kiện chung')
  await expect(page.locator('.message.assistant')).toContainText('Bạn có thể được xem xét bồi thường')
  await expect(page.getByRole('button', { name: /40\/2026/ })).toBeVisible()
  await page.getByRole('button', { name: /40\/2026/ }).click()
  await expect(page.locator('[aria-label="Nguồn căn cứ"]')).toContainText(citation.excerpt)
  await expect(page.getByRole('link', { name: 'Mở trang nguồn gốc' })).toHaveAttribute('href', citation.source_url)
  expect(requests[0].mode).toBe('simple_rag')
})

test('keeps follow-up context and exposes only citizen navigation', async ({ page }) => {
  const requests: Record<string, unknown>[] = []
  await page.route('**/api/v1/chat', route => {
    requests.push(route.request().postDataJSON() as Record<string, unknown>)
    const text = requests.length === 1
      ? 'Bạn đang hỏi về điều kiện bồi thường [S1].'
      : 'Nếu không có giấy chứng nhận, cần kiểm tra thêm nguồn gốc và điều kiện sử dụng đất [S1].'
    return route.fulfill({
      contentType: 'text/event-stream',
      body: `event: result\ndata: ${JSON.stringify(answer(text))}\n\n`,
    })
  })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Hỏi đáp', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Văn bản pháp luật', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Đánh giá hệ thống', exact: true })).toHaveCount(0)
  await send(page, 'Tôi có sổ đỏ thì sao?')
  await send(page, 'Còn nếu không có giấy chứng nhận?')
  await expect(page.locator('.message.assistant')).toHaveCount(2)
  expect(requests[1].history).toEqual(expect.arrayContaining([
    expect.objectContaining({ role: 'user', content: 'Tôi có sổ đỏ thì sao?' }),
  ]))
})

test('shows provider failures without fabricating an answer', async ({ page }) => {
  await page.route('**/api/v1/chat', route => route.fulfill({
    status: 429,
    headers: { 'Retry-After': '30' },
    json: { detail: 'limited' },
  }))
  await page.goto('/')
  await send(page, 'Điều kiện hỗ trợ là gì?')
  await expect(page.getByRole('alert')).toContainText('30 giây')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
})
