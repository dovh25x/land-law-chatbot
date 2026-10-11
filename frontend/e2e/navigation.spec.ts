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

test('API quota errors are displayed without an invented answer', async ({ page }) => {
  await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'test-session', token: 'test-session-token' } }))
  await page.route('**/api/v1/chat', r => r.fulfill({ status: 429, headers: { 'Retry-After': '37' }, json: { detail: 'limited' } }))
  await page.goto('/')
  await page.getByLabel('Câu hỏi pháp luật').fill('Cần kiểm tra điều kiện bồi thường nào?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.getByRole('alert')).toContainText('37 giây')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
})
