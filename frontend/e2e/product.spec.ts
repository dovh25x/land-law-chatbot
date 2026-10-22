import { test, expect, type Page } from '@playwright/test'

const law = { id:'law-product',title:'Quy định về bồi thường và hỗ trợ',document_number:'1/2024/QĐ-UBND',source_kind:'legal',checked_at:'2026-10-11T00:00:00Z',url:'https://hanoi.gov.vn/',applicability_verified:true }
const reference = { ...law,id:'reference-product',title:'Tài liệu gốc bổ sung',availability:'reference_only',applicability_verified:false,attachment_urls:['https://datafiles.chinhphu.vn/source.pdf'] }
const result = (id:number) => ({trace_id:`answer-${id}`,status:'answered',content:'Đáp án fixture, không phải kết luận pháp lý.',citations:[],trace:[],model:'fixture',llm_calls:0})
const send = async (page:Page, text:string) => { await page.getByLabel('Câu hỏi pháp luật').fill(text);await page.getByRole('button',{name:'Gửi câu hỏi'}).click() }
test.beforeEach(async({page}) => {
  await page.route('**/readyz', r=>r.fulfill({json:{status:'ready',database:true}}))
  await page.route('**/api/v1/status', r=>r.fulfill({json:{generation_available:true,reason:null}}))
  await page.route('**/api/v1/documents**',r=>r.fulfill({json:{documents:[law],references:[reference]}}))
  await page.route('**/api/v1/documents/reference-product',r=>r.fulfill({json:{document:{...reference,chunks:[]},relations:[]}}))
  await page.route('**/api/v1/evaluations/latest',r=>r.fulfill({json:{status:'not_run'}}))
  await page.route('**/api/v1/sessions',r=>r.fulfill({status:201,json:{session_id:'fixture',token:'fixture-token'}}))
  await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:`event: result\ndata: ${JSON.stringify(result(1))}\n\n`}))
})
test('landing suggestions cover capabilities and legal topics without auto-send',async({page})=>{
  let posts=0
  page.on('request',request=>{if(request.url().endsWith('/chat'))posts++})
  await page.goto('/')
  const suggestions=page.locator('.topic-grid button')
  await expect(suggestions).toHaveCount(4)
  const labels=await suggestions.allInnerTexts()
  expect(new Set(labels).size).toBe(4)
  for(let index=0;index<labels.length;index++){
    await suggestions.nth(index).click()
    await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue(labels[index])
    await expect(page.getByLabel('Câu hỏi pháp luật')).toBeFocused()
  }
  expect(posts).toBe(0)
})
test('library supports accent-free search and opens reference-only originals',async({page})=>{
  await page.goto('/')
  const menu=page.getByRole('button',{name:'Mở menu điều hướng'});if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'Văn bản pháp luật',exact:true}).click()
  await expect(page.locator('.document-row')).toHaveCount(2)
  await page.getByLabel('Tìm văn bản').fill('boi thuong')
  await expect(page.locator('.document-row')).toHaveCount(1)
  await page.getByLabel('Tìm văn bản').fill('tai lieu goc')
  await page.locator('.document-row').click()
  await expect(page.locator('.source-card')).toContainText('không được dùng làm căn cứ')
  await expect(page.getByRole('link',{name:'Mở bản gốc 1'})).toHaveAttribute('href','https://datafiles.chinhphu.vn/source.pdf')
})
test('expired in-memory session restores the draft and never automatically resends',async({page})=>{
  let sessions=0,chats=0
  await page.route('**/api/v1/sessions',r=>r.fulfill({status:201,json:{session_id:`s${++sessions}`,token:'fixture-token'}}))
  await page.route('**/api/v1/chat',r=>{
    chats++
    return chats===2 ? r.fulfill({status:404,json:{detail:'Session missing'}}) : r.fulfill({contentType:'text/event-stream',body:`event: result\ndata: ${JSON.stringify(result(chats))}\n\n`})
  })
  await page.goto('/');await send(page,'Câu đầu')
  await expect(page.locator('.message.assistant')).toHaveCount(1)
  await send(page,'Câu hỏi cần gửi lại')
  await expect(page.getByRole('alert')).toContainText('Phiên đã hết hạn')
  await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue('Câu hỏi cần gửi lại')
  expect(chats).toBe(2)
  expect(await page.evaluate(()=>sessionStorage.getItem('landlaw-session'))).toBeNull()
  await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
  await expect(page.locator('.message.assistant')).toHaveCount(2)
  expect(sessions).toBe(2);expect(chats).toBe(3)
  await expect(page.locator('.message.user')).toHaveCount(2)
})
test('blocked sessionStorage does not prevent chat within the current tab',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(window,'sessionStorage',{get(){throw new DOMException('blocked','SecurityError')}}))
  await page.goto('/');await send(page,'Câu hỏi fixture')
  await expect(page.locator('.message.assistant')).toBeVisible()
})
test('generation availability refreshes after a provider cooldown',async({page})=>{
  await page.clock.install();let calls=0,limited=true
  await page.route('**/api/v1/status',r=>{calls++;return r.fulfill({json:limited?{generation_available:false,reason:'provider_limited',retry_after:1}:{generation_available:true,reason:null}})})
  await page.goto('/')
  await expect(page.locator('.connection-note')).toContainText('Nhà cung cấp AI đang giới hạn')
  limited=false
  await page.clock.fastForward(1100)
  await expect(page.locator('.connection-note')).toHaveCount(0)
  expect(calls).toBeGreaterThan(1)
  await send(page,'Câu hỏi fixture');await expect(page.locator('.message.assistant')).toBeVisible()
})
