// Five-minute silent screen recording of the real deployed site. No mocks.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
const out='reports/submission'
await mkdir(`${out}/video`,{recursive:true})
const browser=await chromium.launch({headless:true})
const context=await browser.newContext({viewport:{width:1280,height:800},recordVideo:{dir:`${out}/video`,size:{width:1280,height:800}}})
const page=await context.newPage()
const receipt={started_at:new Date().toISOString(),url:'https://hanoi-land-law.pages.dev',narration:false,mocks:false,checks:{}}
const wait=async seconds=>{for(let i=0;i<seconds;i++) await page.waitForTimeout(1000)}
try {
 await page.goto(receipt.url,{waitUntil:'networkidle',timeout:150000})
 await page.getByRole('note').waitFor({timeout:150000})
 receipt.checks.label=await page.getByRole('note').innerText()
 await page.screenshot({path:`${out}/website.png`,fullPage:true})
 await wait(20)
 await page.getByLabel('Thời điểm áp dụng, để trống là hôm nay').fill('2024-08-02')
 await page.getByLabel('Câu hỏi pháp luật').fill('Điều 104 Luật Đất đai 2024 quy định bồi thường chi phí di chuyển tài sản như thế nào?')
 await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
 await page.locator('.message.assistant').waitFor({timeout:150000})
 receipt.checks.answer=await page.locator('.message.assistant .message-body').innerText()
 await wait(25)
 if(await page.locator('.citations button').count()) {
  await page.locator('.citations button').first().click();await wait(25);await page.keyboard.press('Escape')
 }
 if(await page.getByRole('button',{name:/Xem quá trình kiểm chứng/}).count()) {
  await page.getByRole('button',{name:/Xem quá trình kiểm chứng/}).click();await wait(25);await page.keyboard.press('Escape')
 }
 await page.getByRole('button',{name:'Thư viện văn bản',exact:true}).click();await wait(30)
 await page.getByRole('button',{name:'Dự án trọng điểm',exact:true}).click();await wait(30)
 await page.getByRole('button',{name:'Đánh giá hệ thống',exact:true}).click();await wait(25)
 await page.getByRole('button',{name:'Hỏi đáp pháp luật',exact:true}).click()
 const elapsed=(Date.now()-Date.parse(receipt.started_at))/1000
 if(elapsed<300) await wait(Math.ceil(300-elapsed))
 receipt.status='recorded';receipt.seconds=(Date.now()-Date.parse(receipt.started_at))/1000
} catch(e) {receipt.status='partial';receipt.error=e.name;process.exitCode=1}
finally {
 const video=page.video();await context.close()
 if(video) await video.saveAs(`${out}/demo-silent.webm`)
 await browser.close()
 await writeFile(`${out}/video.json`,JSON.stringify(receipt,null,2)+'\n')
 console.log(JSON.stringify({status:receipt.status,seconds:receipt.seconds}))
}
