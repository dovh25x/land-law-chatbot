import {test,expect,type Page} from '@playwright/test'
async function menu(page:Page){const b=page.getByRole('button',{name:'Mở menu điều hướng'});if(await b.isVisible())await b.click()}
test.beforeEach(async({page})=>{
 await page.route('**/readyz',r=>r.fulfill({json:{status:'ready'}}))
 await page.route('**/api/v1/documents',r=>r.fulfill({json:{documents:[]}}))
 await page.route('**/api/v1/projects',r=>r.fulfill({json:{projects:[]}}))
 await page.route('**/api/v1/evaluations/latest',r=>r.fulfill({json:{status:'not_run'}}))
 await page.route('**/api/v1/sessions',r=>r.fulfill({json:{session_id:'fixture',token:'fixture-token'}}))
 await page.route('**/api/v1/sessions/fixture',r=>r.fulfill({json:{valid:true}}))
})
test('history survives reload, follow-up sends context, deleting local history does not reset API session',async({page})=>{
 const requests:Record<string,unknown>[]=[]
 await page.route('**/api/v1/chat',r=>{
  requests.push(r.request().postDataJSON());return r.fulfill({contentType:'text/event-stream',body:'event: result\ndata: '+JSON.stringify({trace_id:'turn-'+requests.length,status:'answered',content:'Đáp án fixture đã nhận.',citations:[],trace:[{step:'verify',summary:'Fixture verify',document_ids:[],elapsed_ms:1}],tool_calls:1,elapsed_ms:20})+'\n\n'})
 })
 await page.goto('/');await page.getByLabel('Câu hỏi pháp luật').fill('Câu hỏi lưu cục bộ');await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await expect(page.locator('.message.assistant')).toBeVisible()
 await menu(page);await expect(page.locator('.history-row')).toHaveCount(1)
 await page.reload();await expect(page.locator('.message.assistant')).toContainText('Đáp án fixture')
 await page.getByLabel('Câu hỏi pháp luật').fill('Còn trường hợp này?');await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await expect(page.locator('.message.assistant')).toHaveCount(2)
 expect(requests[1].history).toMatchObject([{role:'user',content:'Câu hỏi lưu cục bộ'},{role:'assistant',content:'Đáp án fixture đã nhận.'}])
 page.on('dialog',dialog=>dialog.accept());await menu(page)
 await page.getByRole('button',{name:'Xóa toàn bộ lịch sử'}).click()
 await expect(page.locator('.history-row')).toHaveCount(0)
 expect(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('landlaw-session')!).token)).toBe('fixture-token')
 await page.reload();await expect(page.locator('.message')).toHaveCount(0)
})
test('expired history is removed when the app opens',async({page})=>{
 await page.goto('/')
 await page.evaluate(()=>new Promise<void>((resolve,reject)=>{const r=indexedDB.open('landlaw-history',1);r.onsuccess=()=>{const db=r.result;const tx=db.transaction('conversations','readwrite');tx.objectStore('conversations').put({id:'expired',title:'Expired',created_at:0,updated_at:0,expires_at:Date.now()-1,messages:[{id:'m',role:'user',content:'Expired marker'}]});tx.oncomplete=()=>{db.close();resolve()};tx.onerror=()=>reject(tx.error)}}))
 await page.reload();await expect(page.getByText('Expired marker',{exact:true})).toHaveCount(0)
 await menu(page);await expect(page.locator('.history-row')).toHaveCount(0)
})

test('active app removes expired history without a reload',async({page})=>{
 await page.clock.install()
 await page.goto('/')
 await page.evaluate(()=>new Promise<void>((resolve,reject)=>{const r=indexedDB.open('landlaw-history',1);r.onsuccess=()=>{const db=r.result,tx=db.transaction('conversations','readwrite');tx.objectStore('conversations').put({id:'soon-expired',title:'Soon expired',created_at:Date.now(),updated_at:Date.now(),expires_at:Date.now()+30000,messages:[{id:'m',role:'user',content:'Active expiration marker'}]});tx.oncomplete=()=>{db.close();resolve()};tx.onerror=()=>reject(tx.error)}}))
 await page.reload();await expect(page.getByText('Active expiration marker',{exact:true})).toBeVisible()
 await page.clock.fastForward(60001)
 await expect(page.getByText('Active expiration marker',{exact:true})).toHaveCount(0)
})

test('storage failure is disclosed without moving history to the server',async({page})=>{
 const historyCalls:string[]=[]
 page.on('request',r=>{if(/\/messages|\/traces\//.test(r.url()))historyCalls.push(r.url())})
 await page.addInitScript(()=>Object.defineProperty(window,'indexedDB',{get(){throw new DOMException('Fixture storage unavailable','QuotaExceededError')}}))
 await page.goto('/')
 await expect(page.getByRole('alert')).toContainText('Không đọc được lịch sử tại máy')
 expect(historyCalls).toEqual([])
})
