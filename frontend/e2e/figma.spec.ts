import { test, expect, type Page } from '@playwright/test'

const law = { id: 'law-ui-fixture', title: 'Văn bản kiểm thử giao diện', document_number: 'UI/TEST', source_kind: 'legal', checked_at: '2026-10-11T00:00:00Z', applicability_verified: true, url: 'https://hanoi.gov.vn/' }
const projectDoc = { ...law, id: 'ring4-ui-fixture', title: 'Nguồn dự án kiểm thử', project: 'ring4', source_kind: 'official_news' }
const projects = ['ring4', 'ring4', 'olympic'].map((id, i) => ({ id, name: ['Vành đai 4 — Vùng Thủ đô', 'Trục cảnh quan sông Hồng', 'Khu đô thị thể thao Olympic'][i], description: 'Hồ sơ công khai trong fixture kiểm thử; không phải xác nhận pháp lý.', source_ids: i === 0 ? ['ring4-ui-fixture'] : [], questions: [`Cần đối chiếu hồ sơ ${id} nào?`] }))

async function navigate(page: Page, name: string) {
  const menu = page.getByRole('button', { name: 'Mở menu điều hướng' })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('button', { name, exact: true }).click()
}

test.beforeEach(async ({ page }) => {
  await page.route('**/readyz', r => r.fulfill({ json: { status: 'ready', database: true, llm_configured: true, corpus_release: 'ui-fixture', publication_profile: 'technical_demo', quality_status: 'acceptance_pending', checked_at: law.checked_at } }))
  await page.route('**/api/v1/documents', r => r.fulfill({ json: { documents: [law, projectDoc] } }))
  await page.route('**/api/v1/projects', r => r.fulfill({ json: { projects } }))
  await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: { status: 'awaiting_review', matches_active_release: false, matches_active_configuration: false, model: 'old-test-model', results: [] } }))
})

test('Figma typography, responsive composer and mobile navigation', async ({ page }, info) => {
  await page.setViewportSize(info.project.name === 'mobile' ? { width: 390, height: 940 } : { width: 1440, height: 1024 })
  await page.goto('/')
  await page.evaluate(() => document.fonts.ready)
  await expect(page.getByRole('heading', { name: /Tìm đúng căn cứ/ })).toBeVisible()
  expect(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Be Vietnam Pro')
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeVisible()
  await expect(page.locator('.topic-grid > button')).toHaveCount(3)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: `../reports/ui-figma-${info.project.name}.png`, fullPage: true })
  if (info.project.name === 'mobile') {
    const opener = page.getByRole('button', { name: 'Mở menu điều hướng' })
    await opener.click()
    await expect(page.getByRole('dialog', { name: 'Menu điều hướng' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Đóng menu', exact: true })).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(opener).toBeFocused()
  }
})

test('library search, document content and keyboard focus stay usable', async ({ page }) => {
  await page.route('**/api/v1/documents/law-ui-fixture', r => r.fulfill({ json: { document: { ...law, chunks: [{ id: 'fixture-chunk', locator: 'Đoạn kiểm thử', text: 'Nội dung kiểm thử giao diện, không phải dữ liệu pháp lý.' }] } } }))
  await page.goto('/')
  await navigate(page, 'Thư viện văn bản')
  await page.getByLabel('Tìm văn bản').fill('không có trong fixture')
  await expect(page.getByRole('heading', { name: 'Không tìm thấy văn bản' })).toBeVisible()
  await page.getByRole('button', { name: 'Xóa từ khóa' }).click()
  await page.getByLabel('Tìm văn bản').fill('UI/TEST')
  const row = page.getByRole('button', { name: /Văn bản kiểm thử giao diện/ }).first()
  await row.click()
  await expect(page.getByRole('dialog', { name: 'Chi tiết nguồn' })).toContainText('Nội dung kiểm thử giao diện')
  await expect(page.getByRole('button', { name: 'Đóng', exact: true })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('link', { name: 'Mở nguồn chính thức' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(row).toBeFocused()
})

test('project selection prepares the actual chat filters and preserves project/date payload', async ({ page }) => {
  let payload: Record<string, unknown> = {}
  await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'fixture-session', token: 'fixture-token' } }))
  await page.route('**/api/v1/chat', async r => {
    payload = r.request().postDataJSON()
    await r.fulfill({ contentType: 'text/event-stream', body: 'event: result\ndata: '+JSON.stringify({ trace_id: 'fixture-trace', status: 'clarification_needed', content: 'Kết quả kiểm thử.', citations: [], trace: [], tool_calls: 0, elapsed_ms: 50 })+'\n\n' })
  })
  await page.goto('/')
  await navigate(page, 'Vành đai 4')
  await expect(page.locator('.project-tabs')).toHaveCount(0)
  await expect(page.locator('.content-page')).toContainText('hiện chỉ hỗ trợ Vành đai 4')
  await page.getByRole('button', { name: 'Hỏi về Vành đai 4' }).click()
  await page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true }).click()
  await expect(page.getByLabel('Dự án', { exact: true })).toHaveValue('ring4')
  await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue(projects[0].questions[0])
  await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
  await page.getByRole('button', { name: 'Xong', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true })).toContainText('Vành đai 4 · 02/08/2024')
  await expect(page.getByLabel('Chế độ truy xuất')).toHaveCount(0)
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant')).toContainText('Kết quả kiểm thử.')
  expect(payload).toMatchObject({ project: 'ring4', as_of: '2024-08-02' })
})

test('evaluation makes a mismatched report explicit instead of presenting invented metrics', async ({ page }) => {
  await page.goto('/')
  await navigate(page, 'Đánh giá hệ thống')
  await expect(page.getByRole('status')).toContainText('Chưa hoàn tất đánh giá trên cấu hình đang hoạt động')
  await expect(page.locator('.evaluation-summary')).toContainText('Chưa có báo cáo khớp')
  await expect(page.locator('.evaluation-details pre')).toHaveCount(0)
  await expect(page.getByText('old-test-model')).toBeVisible()
})

test('compact header preserves data disclosure and returns keyboard focus', async ({ page }, info) => {
  await page.goto('/')
  const header = await page.locator('.topbar').boundingBox()
  const workspace = await page.locator('.chat-workspace').boundingBox()
  expect(header!.height).toBe(56)
  expect(workspace!.y).toBe(56)
  const infoButton = page.getByRole('button', { name: 'Thông tin dữ liệu và kết nối' })
  await infoButton.click()
  await expect(page.getByRole('dialog')).toContainText('chưa được thẩm định pháp lý độc lập')
  await expect(page.getByRole('dialog')).toContainText('11/10/2026')
  await page.keyboard.press('Escape')
  await expect(infoButton).toBeFocused()
  await page.screenshot({ path: `../reports/ui-compact-${info.project.name}.png`, fullPage: true })
})

test('scope controls fit a narrow screen and can be reset without submitting chat', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 667 })
  await page.goto('/')
  const trigger = page.getByRole('button', { name: 'Phạm vi tra cứu', exact: true })
  await trigger.click()
  await page.getByLabel('Dự án', { exact: true }).selectOption('ring4')
  await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
  const popup = await page.getByRole('group', { name: 'Thiết lập phạm vi tra cứu' }).boundingBox()
  expect(popup!.y).toBeGreaterThanOrEqual(56)
  expect(popup!.x + popup!.width).toBeLessThanOrEqual(320)
  await page.getByRole('button', { name: 'Xong', exact: true }).click()
  await expect(trigger).toContainText('Vành đai 4 · 02/08/2024')
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeInViewport()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await trigger.click()
  await expect(page.getByLabel('Dự án', { exact: true })).toHaveValue('ring4')
  await page.getByRole('button', { name: 'Đặt lại', exact: true }).click()
  await page.keyboard.press('Escape')
  await expect(trigger).toBeFocused()
  await expect(trigger).toHaveText('Phạm vi')
  await expect(page.locator('.message')).toHaveCount(0)
})
