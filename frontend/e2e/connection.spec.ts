import { test, expect, type Page } from '@playwright/test'

/**
 * Deterministic reproduction of the production soft-lock: a failed
 * GET /api/v1/status or /api/v1/documents must never erase verified
 * capabilities, disable the composer after a healthy session, or cancel an
 * answer in progress. Recovery must happen without pressing "Kiểm tra kết nối".
 */

const OK = {
  generation_available: true, reason: null, api_version: 3, source_lookup_only: false,
  capabilities: { citizen_answers: true, answer_schema_version: 2 },
}

const ANSWER = {
  trace_id: 'connection-fixture', status: 'answered', content: 'Nội dung đã kiểm chứng cho tình huống fixture.',
  as_of: '2026-10-22', answer_schema_version: 2, model: 'fixture', embedding_model: 'fixture', mode: 'simple_rag',
  llm_calls: 1, tool_calls: 0, token_usage: 0, elapsed_ms: 5, support_level: 'direct',
  verified_claims: [{ text: 'Nội dung đã kiểm chứng cho tình huống fixture.', citation_ids: ['conn-source-1'] }],
  answer_sections: [{ kind: 'direct', claim_indexes: [0] }],
  citations: [{
    id: 'conn-source-1', document_id: 'fixture-doc', title: 'Nguồn kiểm thử', document_number: '40/2026/QĐ-UBND',
    url: 'https://hanoi.gov.vn/', locator: 'Điều 9', excerpt: 'Đoạn nguồn của fixture.', checked_at: '2026-10-22', applicability: 'current',
  }],
  trace: [],
}

async function baseMocks(page: Page, options: { status?: () => unknown; documents?: () => unknown; chatDelayMs?: number; onChat?: () => void } = {}) {
  await page.route('**/readyz', route => route.fulfill({ json: { status: 'ready', database: true } }))
  await page.route('**/api/v1/status*', route => {
    const body = options.status ? options.status() : OK
    if (body instanceof Error) return route.fulfill({ status: 503, json: { detail: { code: 'starting' } } })
    return route.fulfill({ json: body })
  })
  await page.route('**/api/v1/documents*', route => {
    const body = options.documents ? options.documents() : { documents: [], references: [] }
    if (body instanceof Error) return route.fulfill({ status: 500, json: { detail: 'test_failure' } })
    return route.fulfill({ json: body })
  })
  await page.route('**/api/v1/sessions', route => route.fulfill({ status: 201, json: { session_id: 'fixture', token: 'fixture' } }))
  await page.route('**/api/v1/evaluations*', route => route.fulfill({ json: { status: 'not_run' } }))
  await page.route('**/api/v1/chat', async route => {
    options.onChat?.()
    if (options.chatDelayMs) await new Promise(resolve => setTimeout(resolve, options.chatDelayMs))
    return route.fulfill({ contentType: 'text/event-stream', body: `event: result\ndata: ${JSON.stringify(ANSWER)}\n\n` })
  })
}

const composer = (page: Page) => page.getByLabel('Câu hỏi pháp luật')
const notice = (page: Page) => page.locator('.connection-note')

async function openLibrary(page: Page) {
  if ((page.viewportSize()?.width ?? 1280) < 768) await page.getByRole('button', { name: 'Mở menu điều hướng' }).click()
  await page.getByRole('button', { name: 'Văn bản pháp luật' }).click()
}

test('a transient status failure shows a concise notice, keeps the verified chat usable and recovers automatically', async ({ page }) => {
  let failStatus = false
  await baseMocks(page, { status: () => failStatus ? new Error('down') : OK })
  await page.goto('/')
  await expect(composer(page)).toBeEnabled()

  // A real answer and a citation exist before the connection blips.
  await composer(page).fill('Nhà tôi bị thu hồi đất ở thì có được bồi thường không?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant .message-body')).toContainText('Nội dung đã kiểm chứng')
  await expect(page.locator('.citations button')).toHaveCount(1)

  // Trigger a background status refresh outside the 2s min-gap, and fail it.
  await page.waitForTimeout(2300)
  failStatus = true
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(notice(page)).toContainText('Kết nối đang gián đoạn, hệ thống sẽ tự thử lại')
  await expect(page.locator('body')).not.toContainText('Chưa xác minh được cấu hình hiện tại')
  await expect(composer(page)).toBeEnabled()

  // The answer, message history and citations survive the degraded state.
  await expect(page.locator('.message.assistant .message-body')).toContainText('Nội dung đã kiểm chứng')
  await expect(page.locator('.citations button')).toHaveCount(1)
  await page.locator('.citations button').first().click()
  const panel = page.getByRole('complementary', { name: 'Nguồn căn cứ' }).or(page.getByRole('dialog', { name: 'Nguồn căn cứ' }))
  await expect(panel).toContainText('Đoạn nguồn của fixture.')
  await panel.getByRole('button', { name: 'Đóng' }).click()

  // A draft survives the background recovery that happens without any click.
  await composer(page).fill('Câu hỏi đang soạn dở')
  failStatus = false
  await expect(notice(page)).toHaveCount(0, { timeout: 6000 })
  await expect(composer(page)).toBeEnabled()
  await expect(composer(page)).toHaveValue('Câu hỏi đang soạn dở')
})

test('a failing document library never disables the chat', async ({ page }) => {
  await baseMocks(page, { documents: () => new Error('down') })
  await page.goto('/')
  await expect(composer(page)).toBeEnabled()
  await expect(page.locator('body')).not.toContainText('Chưa xác minh được cấu hình hiện tại')
  await composer(page).fill('Điều kiện bồi thường khi thu hồi đất là gì?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant .message-body')).toContainText('Nội dung đã kiểm chứng')

  await openLibrary(page)
  await expect(page.getByRole('heading', { name: 'Chưa tải được thư viện' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Thử tải lại thư viện' })).toBeVisible()
})

test('an answer in progress is not cancelled by a failed status check, and the question is submitted once', async ({ page }) => {
  let failStatus = false
  let chats = 0
  await baseMocks(page, { status: () => failStatus ? new Error('down') : OK, chatDelayMs: 3000, onChat: () => { chats += 1 } })
  await page.goto('/')
  await expect(composer(page)).toBeEnabled()

  await composer(page).fill('Nhà tôi chưa có sổ đỏ thì có được bồi thường không?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.getByRole('button', { name: 'Dừng lượt hỏi' })).toBeVisible()
  await expect(page.locator('.message.user')).toHaveCount(1)

  // Press Enter again while the turn is in flight: never a duplicate POST.
  await composer(page).click()
  await page.keyboard.press('Enter')
  await expect(page.locator('.message.user')).toHaveCount(1)

  // A status refresh fails while the turn is still streaming.
  failStatus = true
  await page.waitForTimeout(2200)
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect(notice(page)).toContainText('Kết nối đang gián đoạn')

  await expect(page.locator('.message.assistant .message-body')).toContainText('Nội dung đã kiểm chứng', { timeout: 10000 })
  expect(chats).toBe(1)
})

test('a Render cold start (503) recovers automatically without pressing the connection button', async ({ page }) => {
  let attempts = 0
  await baseMocks(page, { status: () => { attempts += 1; return attempts <= 2 ? new Error('starting') : OK } })
  await page.goto('/')
  // First verification is unavailable; the controller must retry on its own.
  await expect(composer(page)).toBeDisabled()
  await expect(composer(page)).toBeEnabled({ timeout: 12000 })
  await expect(notice(page)).toHaveCount(0)
  expect(attempts).toBeGreaterThanOrEqual(3)
})

test('explicit generation-disabled and provider-limited states stay authoritative', async ({ page }) => {
  let status: unknown = { generation_available: false, reason: 'provider_limited', retry_after: 30, api_version: 3, source_lookup_only: false }
  await baseMocks(page, { status: () => status })
  await page.goto('/')
  await expect(composer(page)).toBeEnabled()
  await expect(notice(page)).toContainText('Nhà cung cấp AI đang giới hạn')
  await expect(notice(page)).toContainText('Thử lại sau 30 giây')
  await expect(page.getByRole('button', { name: 'Kiểm tra kết nối' })).toBeEnabled()
  // The server's explicit verdict blocks submission even though the draft stays editable.
  await composer(page).fill('Câu hỏi khi nhà cung cấp đang giới hạn')
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeDisabled()
  // The source library remains available while generation is unavailable.
  await openLibrary(page)
  await expect(page.getByRole('heading', { name: 'Thư viện văn bản' })).toBeVisible()
})

test('an expired session restores the draft and stops without replaying the question', async ({ page }) => {
  await page.route('**/readyz', route => route.fulfill({ json: { status: 'ready', database: true } }))
  await page.route('**/api/v1/status*', route => route.fulfill({ json: OK }))
  await page.route('**/api/v1/documents*', route => route.fulfill({ json: { documents: [], references: [] } }))
  await page.route('**/api/v1/sessions', route => route.fulfill({ status: 201, json: { session_id: 'fixture', token: 'fixture' } }))
  await page.route('**/api/v1/evaluations*', route => route.fulfill({ json: { status: 'not_run' } }))
  let chats = 0
  await page.route('**/api/v1/chat', route => { chats += 1; return route.fulfill({ status: 404, json: { detail: { code: 'session_expired' } } }) })
  await page.goto('/')
  await expect(composer(page)).toBeEnabled()
  await composer(page).fill('Nhà tôi bị thu hồi đất thì có được bồi thường không?')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.error-banner')).toContainText('Phiên đã hết hạn')
  expect(chats).toBe(1)
  await expect(composer(page)).toHaveValue('Nhà tôi bị thu hồi đất thì có được bồi thường không?')
  await expect(composer(page)).toBeEnabled()
})
