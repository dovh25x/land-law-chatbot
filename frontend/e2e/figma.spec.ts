import { test, expect, type Page } from '@playwright/test'

const law = { id: 'law-ui-fixture', title: 'Văn bản kiểm thử giao diện', document_number: 'UI/TEST', source_kind: 'legal', checked_at: '2026-10-11T00:00:00Z', applicability_verified: true, url: 'https://hanoi.gov.vn/' }
const projectDoc = { ...law, id: 'ring4-ui-fixture', title: 'Nguồn dự án kiểm thử', project: 'ring4', source_kind: 'official_news' }
const projects = ['ring4', 'songhong', 'olympic'].map((id, i) => ({ id, name: ['Vành đai 4 — Vùng Thủ đô', 'Trục cảnh quan sông Hồng', 'Khu đô thị thể thao Olympic'][i], description: 'Hồ sơ công khai trong fixture kiểm thử; không phải xác nhận pháp lý.', source_ids: i === 0 ? ['ring4-ui-fixture'] : [], questions: [`Cần đối chiếu hồ sơ ${id} nào?`] }))

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

test('project selection prepares the actual chat filters and preserves baseline/date payload', async ({ page }) => {
  let payload: Record<string, unknown> = {}
  await page.route('**/api/v1/sessions', r => r.fulfill({ status: 201, json: { session_id: 'fixture-session', token: 'fixture-token' } }))
  await page.route('**/api/v1/chat', async r => {
    payload = r.request().postDataJSON()
    await r.fulfill({ contentType: 'text/event-stream', body: 'event: result\ndata: '+JSON.stringify({ trace_id: 'fixture-trace', status: 'clarification_needed', content: 'Kết quả kiểm thử.', citations: [], trace: [], tool_calls: 0, elapsed_ms: 50 })+'\n\n' })
  })
  await page.goto('/')
  await navigate(page, 'Dự án trọng điểm')
  await page.getByRole('tab', { name: 'Sông Hồng', exact: true }).click()
  await expect(page.getByRole('tabpanel')).toContainText('Trục cảnh quan sông Hồng')
  await page.getByRole('button', { name: 'Hỏi về Sông Hồng' }).click()
  await expect(page.getByLabel('Dự án', { exact: true })).toHaveValue('songhong')
  await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue(projects[1].questions[0])
  await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
  await page.getByLabel('Chế độ truy xuất').selectOption('baseline')
  await page.getByRole('button', { name: 'Gửi câu hỏi' }).click()
  await expect(page.locator('.message.assistant')).toContainText('Kết quả kiểm thử.')
  expect(payload).toMatchObject({ project: 'songhong', as_of: '2024-08-02', mode: 'baseline' })
})

test('evaluation makes a mismatched report explicit instead of presenting invented metrics', async ({ page }) => {
  await page.goto('/')
  await navigate(page, 'Đánh giá đồ án')
  await expect(page.getByRole('status')).toContainText('Chưa hoàn tất đánh giá trên cấu hình đang hoạt động')
  await expect(page.locator('.evaluation-summary')).toContainText('Chưa có báo cáo khớp')
  await expect(page.getByText('old-test-model')).toBeHidden()
  await page.getByText('Chi tiết báo cáo · awaiting_review').click()
  await expect(page.locator('.evaluation-details pre')).toContainText('old-test-model')
})
