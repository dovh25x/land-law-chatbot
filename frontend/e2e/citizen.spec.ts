import { test, expect } from '@playwright/test'

test.beforeEach(async({page})=>{
 await page.route('**/readyz',r=>r.fulfill({json:{status:'ready',database:true}}))
 await page.route('**/api/v1/status',r=>r.fulfill({json:{generation_available:true,reason:null,api_version:3,capabilities:{citizen_answers:true,answer_schema_version:2}}}))
 await page.route('**/api/v1/documents',r=>r.fulfill({json:{documents:[]}}))
 await page.route('**/api/v1/evaluations/latest',r=>r.fulfill({json:{status:'not_run'}}))
 await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'fixture',token:'fixture'}}))
})

test('paper clarification can be edited, has an unknown route and survives reload locally',async({page},info)=>{
 const requests:Record<string,unknown>[]=[]
 await page.route('**/api/v1/chat',r=>{
  requests.push(r.request().postDataJSON())
  return r.fulfill({contentType:'text/event-stream',body:`event: result\ndata: ${JSON.stringify({
   trace_id:'citizen-fixture',status:'clarification_needed',content:'Trên giấy ghi tên nào?',citations:[],trace:[],answer_schema_version:2,
   verified_claims:[],answer_sections:[],clarification:{fact:'document_type',question:'Trên giấy ghi tên nào?',options:['Thông báo thu hồi đất','Quyết định thu hồi đất'],allow_unknown:true},
  })}\n\n`})
 })
 await page.goto('/')
 await expect(page.locator('.topic-grid button')).toHaveCount(6)
 await page.locator('.topic-grid button').first().click()
 expect(requests).toHaveLength(0)
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await page.getByRole('button',{name:'Tên khác / Tôi không rõ',exact:true}).click()
 await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue('Tôi không rõ tên giấy.')
 expect(requests).toHaveLength(1)
 await page.evaluate(()=>document.fonts.ready)
 await page.screenshot({path:info.outputPath('citizen-clarification.png'),fullPage:true})
 await page.reload()
 await expect(page.getByRole('button',{name:'Tên khác / Tôi không rõ',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Thông báo thu hồi đất',exact:true}).click()
 await expect(page.getByLabel('Câu hỏi pháp luật')).toHaveValue('Trên giấy ghi: Thông báo thu hồi đất.')
})

test('structured content uses verified claims and exact sources, never an unchecked content summary',async({page})=>{
 await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:`event: result\ndata: ${JSON.stringify({
  trace_id:'structured-fixture',status:'answered',content:'Nội dung không được thay thế claim đã kiểm chứng.',as_of:'2026-10-19',
  answer_schema_version:2,verified_claims:[{text:'Nội dung fixture đã kiểm chứng.',citation_ids:['source-1']}],answer_sections:[{kind:'direct',claim_indexes:[0]}],
  citations:[{id:'source-1',document_id:'fixture',title:'Nguồn kiểm thử',url:'https://hanoi.gov.vn/',locator:'Đoạn kiểm thử',excerpt:'Đoạn nguồn của fixture.',checked_at:'2026-10-19',applicability:'current'}],trace:[],
 })}\n\n`}))
 await page.goto('/')
 await page.getByLabel('Câu hỏi pháp luật').fill('Giải thích một quy định chung.')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await expect(page.locator('.message.assistant .message-body')).toContainText('Nội dung fixture đã kiểm chứng.')
 await expect(page.locator('.message.assistant .message-body')).not.toContainText('không được thay thế')
 await page.getByRole('button',{name:'Mở nguồn 1 của nội dung'}).click()
 await expect(page.getByRole('complementary',{name:'Nguồn căn cứ'}).or(page.getByRole('dialog',{name:'Nguồn căn cứ'}))).toContainText('Đoạn nguồn của fixture.')
})

test('invalid structured references cannot expose content, sources or copy actions',async({page})=>{
 await page.route('**/api/v1/chat',r=>r.fulfill({contentType:'text/event-stream',body:`event: result\ndata: ${JSON.stringify({trace_id:'invalid',status:'answered',content:'Nội dung chưa kiểm chứng.',citations:[],trace:[],answer_schema_version:2,verified_claims:[],answer_sections:[{kind:'direct',claim_indexes:[9]}]})}\n\n`}))
 await page.goto('/')
 await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi fixture')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await expect(page.locator('.message.assistant')).toContainText('dữ liệu không đúng định dạng')
 await expect(page.locator('.message.assistant')).not.toContainText('Nội dung chưa kiểm chứng.')
 await expect(page.locator('.message.assistant .answer-actions')).toHaveCount(0)
})
