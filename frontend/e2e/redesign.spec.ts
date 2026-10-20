import { test, expect, type Page } from '@playwright/test'

const document = { id: 'law-redesign', title: 'Văn bản kiểm thử giao diện có tên dài để kiểm tra bố cục', document_number: 'UI/REDESIGN', source_kind: 'legal', checked_at: '2026-10-17T00:00:00Z', url: 'https://hanoi.gov.vn/', applicability_verified: true }
const citations = [1, 2].map(index => ({ id: `citation-${index}`, document_id: document.id, title: document.title, document_number: `UI/${index}`, url: document.url, locator: `Điều kiểm thử ${index}`, excerpt: `Đoạn căn cứ fixture số ${index}. ` + 'Nội dung dài kiểm tra reflow. '.repeat(10), checked_at: document.checked_at, applicability: index === 1 ? 'current' : 'unrecognized', checksum: 'a'.repeat(64) }))
const result = { trace_id: 'redesign-fixture', status: 'answered', content: '## Đáp án kiểm thử\n\n' + 'Nội dung kiểm thử giao diện, không phải kết luận pháp lý. '.repeat(24), citations, trace: [{ step: 'verify', tool: 'check_effectivity', summary: 'Sự kiện fixture thực tế.', elapsed_ms: 1, document_ids: [document.id] }] }
async function navigate(page: Page, name: string) {
  const menu = page.getByRole('button', { name: 'Mở menu điều hướng' })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('button', { name, exact: true }).click()
}
async function send(page: Page) {
  await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi kiểm thử')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant')).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
}
test.beforeEach(async ({ page }) => {
  await page.route('**/readyz', route => route.fulfill({ json: { status: 'ready', database: true, corpus_release: 'redesign-fixture' } }))
  await page.route('**/api/v1/status', route => route.fulfill({ json: { generation_available: true, reason: null } }))
  await page.route('**/api/v1/documents', route => route.fulfill({ json: { documents: [document] } }))
  await page.route('**/api/v1/evaluations/latest', route => route.fulfill({ json: { status: 'not_run' } }))
  await page.route('**/api/v1/sessions', route => route.fulfill({ json: { session_id: 'redesign', token: 'fixture' } }))
  await page.route('**/api/v1/chat', route => route.fulfill({ contentType: 'text/event-stream', body: `event: result\ndata: ${JSON.stringify(result)}\n\n` }))
})

test('suggestions populate an editable composer without sending a request', async ({ page }) => {
  let posts = 0
  page.on('request', request => { if (request.url().endsWith('/chat')) posts++ })
  await page.goto('/')
  const suggestion = page.locator('.topic-grid button').first()
  const value = await suggestion.innerText()
  await suggestion.click()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue(value)
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeFocused()
  expect(posts).toBe(0)
})

test('source list selects the exact citation and desktop allows parallel input', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.goto('/'); await send(page)
  // Finish the initial smooth scroll before measuring the user's reading position.
  await page.locator('.chat-scroll').evaluate(el => el.scrollTo({ top: el.scrollHeight, behavior: 'instant' }))
  const scroll = await page.locator('.chat-scroll').evaluate(el => el.scrollTop)
  await page.getByRole('button', { name: 'Xem nguồn', exact: true }).click()
  const panel = page.getByRole('complementary', { name: 'Nguồn căn cứ' })
  await expect(panel).toContainText('2 nguồn trong đáp án')
  await expect(panel.locator('blockquote')).toHaveCount(0)
  await panel.getByRole('button', { name: /2 UI\/2/ }).click()
  await expect(panel.locator('blockquote')).toContainText('fixture số 2')
  await expect(panel).toContainText('Chưa xác định trạng thái áp dụng')
  await page.getByLabel('Câu hỏi pháp luật').fill('Có thể nhập tiếp khi đối chiếu')
  await expect(panel).toBeVisible()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeFocused()
  expect(await page.locator('.chat-scroll').evaluate(el => el.scrollTop)).toBeCloseTo(scroll, -1)
  await page.keyboard.press('Escape')
  await expect(panel).toHaveCount(0)
})

test('source changes from comparison to modal when the viewport narrows', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 }); await page.goto('/'); await send(page)
  const opener = page.locator('.citations button').first(); await opener.click()
  await expect(page.getByRole('complementary', { name: 'Nguồn căn cứ' })).toBeVisible()
  await page.setViewportSize({ width: 1024, height: 800 })
  const dialog = page.getByRole('dialog', { name: 'Nguồn căn cứ' })
  await expect(dialog).toHaveAttribute('aria-modal', 'true')
  await dialog.getByRole('button', { name: 'Đóng', exact: true }).focus()
  await page.keyboard.press('Shift+Tab')
  await expect(dialog.getByRole('link', { name: 'Mở nguồn chính thức' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(opener).toBeFocused()
})

test('library distinguishes fetch errors from an unpublished corpus and retries', async ({ page }) => {
  let failed = true
  await page.route('**/api/v1/documents', route => failed ? route.fulfill({ status: 503 }) : route.fulfill({ json: { documents: [] } }))
  await page.goto('/'); await navigate(page, 'Thư viện văn bản')
  await expect(page.getByRole('heading', { name: 'Chưa tải được thư viện' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Corpus chưa được công bố' })).toHaveCount(0)
  failed = false
  await page.getByRole('button', { name: 'Thử tải lại thư viện' }).click()
  await expect(page.getByRole('heading', { name: 'Corpus chưa được công bố' })).toBeVisible()
})

test('library filters source kinds locally and preserves document numbers', async ({ page }) => {
  await page.goto('/'); await navigate(page, 'Thư viện văn bản')
  await expect(page.locator('.document-row')).toContainText('UI/REDESIGN')
  await page.getByLabel('Loại nguồn', { exact: true }).selectOption('official_news')
  await expect(page.getByRole('heading', { name: 'Không tìm thấy văn bản' })).toBeVisible()
  await page.getByRole('button', { name: 'Xóa từ khóa' }).click()
  await expect(page.locator('.document-row')).toHaveCount(1)
})

for (const reason of ['disabled', 'source_stale', 'provider_limited']) {
  test(`generation ${reason} preserves library and does not submit chat`, async ({ page }) => {
    let posts = 0
    await page.route('**/api/v1/status', route => route.fulfill({ json: { generation_available: false, reason, retry_after: reason === 'provider_limited' ? 37 : null } }))
    page.on('request', request => { if (request.url().endsWith('/chat')) posts++ })
    await page.goto('/')
    await expect(page.locator('.connection-note')).toContainText('Thư viện nguồn vẫn truy cập được')
    if (reason === 'provider_limited') await expect(page.locator('.connection-note')).toContainText('37 giây')
    await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi')
    await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
    expect(posts).toBe(0)
    await navigate(page, 'Thư viện văn bản')
    await expect(page.locator('.document-row')).toBeVisible()
  })
}

test('snapshot metadata stays out of the UI, including previously saved answer preambles', async ({ page }) => {
  await page.route('**/api/v1/status', route => route.fulfill({ json: {
    generation_available: true, reason: null, source_fresh: false, warning: 'source_stale',
    source_checked_at: '2026-10-11T17:32:27Z',
  } }))
  let posts = 0
  page.on('request', request => { if (request.url().endsWith('/chat')) posts++ })
  await page.goto('/')
  await expect(page.locator('.connection-note')).toHaveCount(0)
  await page.route('**/api/v1/chat', route => route.fulfill({ contentType: 'text/event-stream', body: 'event: result\ndata: '+JSON.stringify({...result,content:'Nguồn chưa được rà soát cập nhật; nội dung tham khảo từ snapshot, chưa xác nhận quy định hiện hành. Đáp án kiểm thử'})+'\n\n' }))
  await send(page)
  expect(posts).toBe(1)
  await expect(page.locator('.message.assistant')).toContainText('Đáp án kiểm thử')
  await expect(page.locator('.message.assistant')).not.toContainText('Nguồn chưa được rà soát cập nhật')
  await page.reload()
  await expect(page.locator('.message.assistant')).toContainText('Đáp án kiểm thử')
  await expect(page.locator('.message.assistant')).not.toContainText('Nguồn chưa được rà soát cập nhật')
  await page.locator('.topbar .data-trigger').click()
  await expect(page.getByLabel('Dữ liệu và phạm vi sử dụng', { exact: true })).toContainText('Có thể sinh đáp án')
  await expect(page.getByLabel('Dữ liệu và phạm vi sử dụng', { exact: true })).not.toContainText('Nguồn chưa được rà soát cập nhật')
})

test('a disconnected SSE is not retried and never produces a draft', async ({ page }) => {
  let posts = 0
  await page.route('**/api/v1/chat', route => { posts++; return route.fulfill({ contentType: 'text/event-stream', body: 'event: progress\ndata: {"step":"retrieve","summary":"Đang tra cứu","document_ids":[],"elapsed_ms":1}\n\n' }) })
  await page.goto('/')
  await page.getByLabel('Câu hỏi pháp luật').fill('Kiểm thử mất kết nối')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.getByRole('alert')).toContainText('Server không lưu đáp án để khôi phục')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
  expect(posts).toBe(1)
})

test('storage and copy errors retain their own context outside chat', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'indexedDB', { get() { throw new DOMException('Unavailable', 'QuotaExceededError') } })
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async () => { throw new Error('Denied') } } })
  })
  await page.goto('/'); await send(page)
  await page.getByRole('button', { name: 'Sao chép', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Không sao chép được')
  await expect(page.locator('.error-banner')).toHaveCount(0)
  await navigate(page, 'Thư viện văn bản')
  await expect(page.getByRole('alert')).toContainText('lịch sử tại máy')
})

test('touch Enter inserts a newline while IME input does not submit', async ({ page }, info) => {
  await page.goto('/')
  const input = page.getByLabel('Câu hỏi pháp luật')
  await input.fill('Câu hỏi')
  await input.dispatchEvent('keydown', { key: 'Enter', isComposing: true })
  await expect(page.locator('.message.user')).toHaveCount(0)
  if (info.project.name === 'mobile') {
    await input.press('Enter'); await expect(input).toHaveValue('Câu hỏi\n')
    await expect(page.locator('.message.user')).toHaveCount(0)
  } else {
    await input.press('Enter'); await expect(page.locator('.message.assistant')).toBeVisible()
  }
})

test('reading older answers preserves scroll until explicitly returning to the end', async ({ page }) => {
  await page.goto('/'); await send(page)
  await page.locator('.chat-scroll').evaluate(el => { el.scrollTop = 0 })
  await expect(page.getByRole('button', { name: 'Về cuối hội thoại' })).toBeVisible()
  await page.getByRole('button', { name: 'Về cuối hội thoại' }).click()
  await expect(page.getByRole('button', { name: 'Về cuối hội thoại' })).toBeHidden()
})

test('responsive themes preserve touch targets, source access and long content', async ({ page }, info) => {
  test.setTimeout(90000)
  await page.goto('/'); await send(page)
  for (const width of [320, 390, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 960 })
    for (const theme of ['light', 'dark']) {
      await page.evaluate(value => { document.documentElement.dataset.theme = value }, theme)
      await page.locator('.chat-scroll').evaluate(el => { el.scrollTop = el.scrollHeight })
      const input = page.getByLabel('Câu hỏi pháp luật')
      expect(await input.evaluate(el => getComputedStyle(el).fontSize)).toBe('16px')
      const button = await page.getByRole('button', { name: 'Gửi câu hỏi' }).boundingBox()
      expect(button!.width).toBeGreaterThanOrEqual(44); expect(button!.height).toBeGreaterThanOrEqual(44)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.locator('.citations button').last().click()
      await expect(page.locator('.source-excerpt blockquote')).toContainText('fixture số 2')
      await page.getByText('Thông tin phiên bản nguồn', { exact: true }).click()
      await expect(page.locator('.source-technical')).toContainText('a'.repeat(64))
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath(`matrix-${info.project.name}-${width}-${theme}.png`) })
      await page.keyboard.press('Escape')
    }
  }
})

test('cancel during session setup does not send chat or invent an answer', async ({ page }) => {
  let releaseSession: () => void = () => {}
  const pending = new Promise<void>(resolve => { releaseSession = resolve })
  let posts = 0
  await page.route('**/api/v1/sessions', async route => { await pending; await route.fulfill({ json: { session_id: 'cancel-fixture', token: 'fixture' } }) })
  page.on('request', request => { if (request.url().endsWith('/chat')) posts++ })
  await page.goto('/')
  await page.getByLabel('Câu hỏi pháp luật').fill('Kiểm thử dừng')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await page.getByRole('button', { name: 'Dừng lượt hỏi' }).click()
  releaseSession()
  await expect(page.getByRole('alert')).toContainText('Bạn đã dừng lượt hỏi')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
  expect(posts).toBe(0)
})

test('trace exposes observed events without marking every step successful', async ({ page }) => {
  await page.goto('/'); await send(page)
  await page.getByRole('button', { name: 'Xem quá trình kiểm chứng' }).click()
  const panel = page.getByRole('dialog', { name: 'Quá trình kiểm chứng' })
  await expect(panel).toContainText('Kiểm tra căn cứ')
  await expect(panel).toContainText('Sự kiện fixture thực tế')
  await expect(panel.locator('svg.lucide-check')).toHaveCount(0)
  await panel.getByText('Chi tiết công cụ và nguồn').click()
  await expect(panel).toContainText('check_effectivity')
})

test('welcome remains reachable on short narrow screens', async ({ page }) => {
  for (const height of [667, 480]) {
    await page.setViewportSize({ width: 320, height }); await page.goto('/')
    const heading = page.getByRole('heading', { name: 'Bạn đang vướng việc gì?' })
    await expect(heading).toBeInViewport()
    const bounds = await heading.boundingBox()
    expect(bounds!.y).toBeGreaterThanOrEqual(64)
    await page.locator('.chat-workspace').evaluate(el => { el.scrollTop = el.scrollHeight })
    await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeInViewport()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

test('return-to-end control stays above a multiline composer', async ({ page }) => {
  await page.goto('/'); await send(page)
  await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi dài\n'.repeat(30))
  await page.locator('.chat-scroll').evaluate(el => { el.scrollTop = 0 })
  const jump = page.getByRole('button', { name: 'Về cuối hội thoại' })
  await expect(jump).toBeVisible()
  const button = await jump.boundingBox(), composer = await page.locator('.composer').boundingBox()
  expect(button!.y + button!.height).toBeLessThanOrEqual(composer!.y)
  expect(await page.getByLabel('Câu hỏi pháp luật').evaluate(el => el.getBoundingClientRect().height)).toBeLessThanOrEqual(160)
})
