import { expect, test, type Page } from '@playwright/test'

const law = { id: 'reviewed-law', title: 'Văn bản có đoạn được review', document_number: '1/2026', source_kind: 'legal',
  url: 'https://example.test/official-law', checked_at: '2026-10-21', applicability_verified: false,
  source_lookup_only: true, review_as_of: '2026-10-21', verified_passage_count: 4, whole_document_verified: false }

async function seedSavedCitation(page: Page) {
  await page.evaluate(() => new Promise<void>((resolve, reject) => {
    const request = indexedDB.open('landlaw-history', 1)
    request.onsuccess = () => {
      const db = request.result, transaction = db.transaction('conversations', 'readwrite')
      transaction.objectStore('conversations').put({ id: 'pending-metadata-history', title: 'Metadata race fixture',
        created_at: Date.now(), updated_at: Date.now(), expires_at: Date.now() + 86400000,
        messages: [{ id: 'saved-answer', role: 'assistant', content: 'SAVED_ANSWER_PENDING_METADATA',
          result: { status: 'answered', content: 'SAVED_ANSWER_PENDING_METADATA', citations: [
            { id: 'unreviewed-old', document_id: 'unreviewed', title: 'UNTRUSTED_OLD_SOURCE',
              excerpt: 'UNTRUSTED_OLD_EXCERPT', locator: 'Điều 999' }], trace: [] } }] })
      transaction.oncomplete = () => { db.close(); resolve() }
      transaction.onerror = () => reject(transaction.error)
    }
  }))
}

test.beforeEach(async ({ page }) => {
  await page.route('**/readyz', route => route.fulfill({ json: { status: 'ready', database: true, source_lookup_only: true } }))
  await page.route('**/api/v1/status', route => route.fulfill({ json: {
    generation_available: false, reason: 'disabled', source_lookup_only: true, source_lookup_as_of: '2026-10-21',
  } }))
  await page.route('**/api/v1/documents**', route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/reviewed-law')) return route.fulfill({ json: { document: {
      ...law, chunks: [1, 2, 3, 4].map(number => ({ id: `passage-${number}`, locator: `Điều ${number}`, text: `REVIEWED_PASSAGE_${number}` })),
    }, relations: [] } })
    const day = url.searchParams.get('as_of') || '2026-10-21'
    return route.fulfill({ json: { documents: day === '2026-10-21' ? [law] : [], references: [],
      source_lookup_only: true, as_of: day, verified_passage_count: day === '2026-10-21' ? 4 : 0 } })
  })
  await page.route('**/api/v1/evaluations/latest', route => route.fulfill({ json: { status: 'not_run' } }))
})

test('source-only mode disables chat and displays date-pinned reviewed excerpts', async ({ page }) => {
  const chatRequests: string[] = []
  page.on('request', request => { if (request.url().endsWith('/api/v1/chat')) chatRequests.push(request.url()) })
  await page.goto('/')
  await expect(page.getByRole('note').filter({ hasText: 'chỉ tra cứu đoạn nguồn đã review' })).toBeVisible()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeDisabled()
  await page.getByRole('button', { name: 'Mở thư viện nguồn đã review' }).click()
  await page.locator('.document-row').click()
  await expect(page.locator('.source-card')).toContainText('Không phải đáp án được model kiểm chứng')
  await expect(page.getByText('REVIEWED_PASSAGE_4', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Mở nguồn chính thức', exact: true })).toHaveAttribute('href', law.url)
  await page.getByRole('button', { name: 'Đóng', exact: true }).click()
  await page.getByLabel('Thời điểm áp dụng nguồn').fill('2026-10-22')
  const updated = page.waitForRequest(request => request.url().endsWith('/api/v1/documents?as_of=2026-10-22'))
  await page.getByRole('button', { name: 'Đối chiếu ngày đã chọn' }).click()
  await updated
  await expect(page.locator('.document-row')).toHaveCount(0)
  expect(chatRequests).toEqual([])
})

test('retains local history but never treats saved citations as reviewed current evidence', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeDisabled()
  await page.evaluate(() => new Promise<void>((resolve, reject) => {
    const request = indexedDB.open('landlaw-history', 1)
    request.onsuccess = () => {
      const db = request.result, transaction = db.transaction('conversations', 'readwrite')
      transaction.objectStore('conversations').put({ id: 'old', title: 'Lịch sử cũ', created_at: Date.now(),
        updated_at: Date.now(), expires_at: Date.now() + 86400000, messages: [{ id: 'old-answer', role: 'assistant',
          content: 'OLD_ANSWER_BODY', result: { status: 'answered', content: 'OLD_ANSWER_BODY', trace_id: 'old',
            citations: [{ id: 'old-source', document_id: 'unreviewed', title: 'OLD_UNREVIEWED_CITATION',
              excerpt: 'OLD_UNREVIEWED_EXCERPT', locator: 'Điều 999' }], trace: [] } }] })
      transaction.oncomplete = () => { db.close(); resolve() }
      transaction.onerror = () => reject(transaction.error)
    }
  }))
  await page.reload()
  await expect(page.locator('.message.assistant')).toContainText('OLD_ANSWER_BODY')
  await expect(page.locator('.message.assistant')).toContainText('chưa được xác minh lại')
  await expect(page.getByText('OLD_UNREVIEWED_CITATION')).toHaveCount(0)
  await expect(page.getByText('OLD_UNREVIEWED_EXCERPT')).toHaveCount(0)
  await expect(page.locator('.citations')).toHaveCount(0)
})

test('delayed metadata never exposes saved citations or enables generation while configuration is unknown', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Mở thư viện nguồn đã review' })).toBeVisible()
  await seedSavedCitation(page)
  let releaseStatus!: () => void
  const pending = new Promise<void>(resolve => { releaseStatus = resolve })
  await page.route('**/api/v1/status', async route => {
    await pending
    await route.fulfill({ json: { generation_available: false, reason: 'disabled',
      source_lookup_only: true, source_lookup_as_of: '2026-10-21' } })
  })
  try {
    await page.reload()
    await expect(page.locator('.message.assistant')).toContainText('SAVED_ANSWER_PENDING_METADATA')
    await expect(page.locator('.message.assistant')).toContainText('chưa được xác minh lại')
    await expect(page.locator('.citations')).toHaveCount(0)
    await expect(page.locator('.answer-actions')).toHaveCount(0)
    await expect(page.locator('.citizen-section')).toHaveCount(0)
    await expect(page.getByLabel('Câu hỏi pháp luật')).toBeDisabled()
    await expect(page.locator('iframe[src*="challenges.cloudflare.com"]')).toHaveCount(0)
    await expect(page.getByText('UNTRUSTED_OLD_EXCERPT')).toHaveCount(0)
  } finally { releaseStatus() }
  await expect(page.getByRole('button', { name: 'Mở thư viện nguồn đã review' })).toBeVisible()
  await expect(page.locator('.message.assistant')).toContainText('chưa được xác minh lại')
  await expect(page.locator('.citations')).toHaveCount(0)
})

test('failed metadata does not reuse a previously enabled normal configuration', async ({ page }) => {
  await page.route('**/api/v1/status', route => route.fulfill({ json: { generation_available: true, reason: null } }))
  await page.route('**/api/v1/documents**', route => route.fulfill({ json: { documents: [], references: [] } }))
  await page.goto('/')
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeEnabled() // Known normal mode still works.
  await seedSavedCitation(page)
  await page.route('**/api/v1/status', route => route.fulfill({ status: 503, json: { detail: 'metadata unavailable fixture' } }))
  await page.reload()
  await expect(page.locator('.connection-note')).toContainText('Chưa xác minh được cấu hình hiện tại')
  await expect(page.locator('.message.assistant')).toContainText('chưa được xác minh lại')
  await expect(page.locator('.citations')).toHaveCount(0)
  await expect(page.locator('.answer-actions')).toHaveCount(0)
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeDisabled()
  await expect(page.getByText('UNTRUSTED_OLD_EXCERPT')).toHaveCount(0)
  // A status-only focus refresh must not revive an incomplete full configuration.
  await page.route('**/api/v1/status', route => route.fulfill({ json: { generation_available: true, reason: null } }))
  const unexpected = page.waitForResponse(response => response.url().endsWith('/api/v1/status') && response.ok(), { timeout: 700 }).catch(() => null)
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  expect(await unexpected).toBeNull()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeDisabled()
  await page.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }).click()
  await expect(page.getByLabel('Câu hỏi pháp luật')).toBeEnabled()
})
