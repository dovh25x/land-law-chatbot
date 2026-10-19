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
  await page.route('**/api/v1/status', r => r.fulfill({ json: { generation_available: true, reason: null } }))
  await page.route('**/readyz', r => r.fulfill({ json: { status: 'ready', database: true, llm_configured: true, corpus_release: 'ui-fixture', publication_profile: 'technical_demo', quality_status: 'acceptance_pending', checked_at: law.checked_at } }))
  await page.route('**/api/v1/documents', r => r.fulfill({ json: { documents: [law, projectDoc] } }))
  await page.route('**/api/v1/projects', r => r.fulfill({ json: { projects } }))
  await page.route('**/api/v1/evaluations/latest', r => r.fulfill({ json: { status: 'awaiting_review', matches_active_release: false, matches_active_configuration: false, model: 'old-test-model', results: [] } }))
})

test('Figma typography, responsive composer and mobile navigation', async ({ page }, info) => {
  await page.setViewportSize(info.project.name === 'mobile' ? { width: 390, height: 940 } : { width: 1440, height: 1024 })
  await page.goto('/')
  await page.evaluate(() => document.fonts.ready)
  await expect(page.getByRole('heading', { name: /Bạn muốn tìm hiểu điều gì/ })).toBeVisible()
  expect(await page.locator('body').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Be Vietnam Pro')
  await expect(page.getByRole('button', { name: 'Gửi câu hỏi' })).toBeVisible()
  await expect(page.locator('.topic-grid > button')).toHaveCount(3)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: info.outputPath(`ui-figma-${info.project.name}.png`), fullPage: true })
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
  await expect(page.locator('[aria-label="Nguồn căn cứ"]')).toContainText('Nội dung kiểm thử giao diện')
  await expect(page.getByRole('button', { name: 'Đóng', exact: true })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  if (page.viewportSize()!.width < 1280) await expect(page.getByRole('link', { name: 'Mở nguồn chính thức' })).toBeFocused()
  else expect(await page.locator('[aria-label="Nguồn căn cứ"]').evaluate(el => el.contains(document.activeElement))).toBe(false)
  await page.keyboard.press('Escape')
  await expect(row).toBeFocused()
})

test('chat fixes ring4 scope and sends an idempotency key', async ({page})=>{
 let payload:Record<string,unknown>={}
 await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'fixture',token:'fixture'}}))
 await page.route('**/api/v1/chat',r=>{payload=r.request().postDataJSON();return r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: '+JSON.stringify({trace_id:'fixed-scope',status:'clarification_needed',content:'Kết quả kiểm thử.',citations:[],trace:[],tool_calls:0,elapsed_ms:50})+'\n\n'})})
 await page.goto('/')
 await expect(page.getByLabel('Dự án',{exact:true})).toHaveCount(0)
 await expect(page.getByLabel('Chế độ truy xuất')).toHaveCount(0)
 await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi kiểm thử')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await expect(page.locator('.message.assistant')).toBeVisible()
 expect(payload).toMatchObject({project:'ring4',history:[]})
 expect(payload.request_id).toMatch(/^[0-9a-f-]{36}$/)
})

test('evaluation makes a mismatched report explicit instead of presenting invented metrics', async ({ page }) => {
  await page.goto('/')
  await navigate(page, 'Đánh giá hệ thống')
  await expect(page.getByRole('status')).toContainText('Chưa hoàn tất đánh giá trên cấu hình đang hoạt động')
  await expect(page.locator('.evaluation-summary')).toContainText('Chưa có báo cáo khớp')
  await expect(page.locator('.evaluation-details pre')).toHaveCount(0)
  await expect(page.getByText('old-test-model')).toBeHidden()
  await page.getByText('Xem báo cáo của phiên bản trước', { exact: true }).click()
  await expect(page.getByText('old-test-model')).toBeVisible()
})

test('compact header preserves data disclosure and returns keyboard focus', async ({ page }, info) => {
  await page.goto('/')
  const header = await page.locator('.topbar').boundingBox()
  const workspace = await page.locator('.chat-workspace').boundingBox()
  expect(header!.height).toBe(64)
  expect(workspace!.y).toBe(header!.height)
  if(info.project.name==='mobile') await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
  const infoButton = page.getByRole('button', { name: 'Thông tin dữ liệu và kết nối' }).filter({visible:true})
  await infoButton.click()
  await expect(page.getByRole('dialog')).toContainText('chưa được thẩm định pháp lý độc lập')
  await expect(page.getByRole('dialog')).toContainText('11/10/2026')
  await page.keyboard.press('Escape')
  if(info.project.name==='desktop') await expect(infoButton).toBeFocused()
  await page.screenshot({ path: info.outputPath(`ui-compact-${info.project.name}.png`), fullPage: true })
})

test('theme and navigation fit a narrow screen',async({page})=>{
 await page.setViewportSize({width:320,height:667});await page.goto('/')
 await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
 const root=page.locator('html');const before=await root.getAttribute('data-theme')
 await page.getByRole('button',{name:'Đổi giao diện sáng tối'}).click()
 expect(await root.getAttribute('data-theme')).not.toBe(before)
 await page.keyboard.press('Escape')
 await expect(page.getByRole('button',{name:'Gửi câu hỏi'})).toBeInViewport()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})

test('revised Figma answer actions copy text and preserve light/dark source access',async({page},info)=>{
 await page.setViewportSize(info.project.name==='mobile'?{width:390,height:844}:{width:1440,height:960})
 await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text:string)=>{(window as unknown as {copied:string}).copied=text}}}))
 const content='## Chi phí di chuyển tài sản\n\nNội dung fixture kiểm tra giao diện; không phải đáp án pháp lý.'
 const citation={id:'design-source',document_id:law.id,title:law.title,document_number:'UI/TEST',url:law.url,locator:'Điều kiểm thử',excerpt:'Đoạn nguồn fixture.',checked_at:law.checked_at,applicability:'current'}
 await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'design',token:'fixture'}}))
 await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: '+JSON.stringify({trace_id:'design-answer',status:'answered',content,citations:[citation],trace:[],tool_calls:1,elapsed_ms:50})+'\n\n'}))
 await page.goto('/')
 await page.getByLabel('Câu hỏi pháp luật').fill('Khi bị thu hồi đất, chi phí di chuyển tài sản được quy định như thế nào?')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await page.getByRole('button',{name:'Sao chép',exact:true}).click()
 expect(await page.evaluate(()=>(window as unknown as {copied:string}).copied)).toBe(content)
 await expect(page.getByRole('button',{name:'Đã sao chép'})).toBeVisible()
 await page.evaluate(()=>document.fonts.ready)
 await page.screenshot({path:info.outputPath(`ui-revision-chat-${info.project.name}-light.png`)})
 await page.getByRole('button',{name:'Xem nguồn',exact:true}).click()
 await page.getByRole('navigation',{name:'Nguồn của đáp án'}).getByRole('button').first().click()
 await expect(page.locator('[aria-label="Nguồn căn cứ"]')).toContainText(citation.excerpt)
 await page.screenshot({path:info.outputPath(`ui-revision-source-${info.project.name}.png`)})
 await page.keyboard.press('Escape')
 if(info.project.name==='mobile') await page.getByRole('button',{name:'Mở menu điều hướng'}).click()
 await page.getByRole('button',{name:'Đổi giao diện sáng tối'}).click()
 if(info.project.name==='mobile') await page.keyboard.press('Escape')
 await page.screenshot({path:info.outputPath(`ui-revision-chat-${info.project.name}-dark.png`)})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})
