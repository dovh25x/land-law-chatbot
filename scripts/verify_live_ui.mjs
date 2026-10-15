// Real public UI, without API interception or fabricated answers.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { writeFile, mkdir } from 'node:fs/promises'
const browser=await chromium.launch({headless:true})
const checks=[]
try {
 for(const width of [1440,390,320]) {
  const page=await browser.newPage({viewport:{width,height:800}})
  await page.goto('https://hanoi-land-law.pages.dev',{waitUntil:'networkidle'})
  await page.getByLabel('Câu hỏi pháp luật').waitFor()
  if(await page.getByLabel('Chế độ truy xuất').count())throw Error('Unexpected mode selector')
  await page.getByRole('button',{name:'Phạm vi tra cứu',exact:true}).click()
  const values=await page.locator('#project option').evaluateAll(options=>options.map(o=>o.value))
  if(values.some(v=>v && v!=='ring4'))throw Error('Unsupported project selectable')
  await page.keyboard.press('Escape')
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow')
  const menu=page.getByRole('button',{name:'Mở menu điều hướng'})
  if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'Vành đai 4',exact:true}).click()
  await page.getByRole('heading',{name:'Vành đai 4',exact:true}).waitFor()
  if(!await page.locator('.content-page').innerText().then(t=>t.includes('hiện chỉ hỗ trợ Vành đai 4')))throw Error('Scope disclosure missing')
  if(await page.getByRole('tab').count())throw Error('Unexpected project tabs')
  if(width===1440 && process.argv.includes('--chat')) {
    await page.getByRole('button',{name:'Đánh giá đồ án',exact:true}).click()
    await page.locator('.evaluation-table tbody tr').last().waitFor()
    if(await page.locator('.evaluation-table tbody tr').count()!==20)throw Error('Twenty-case table missing')
    if(await page.locator('.evaluation-details pre').count())throw Error('Raw JSON exposed as evaluation UI')
    checks.push({reviewed_evaluation_rows:20})
    await page.getByRole('button',{name:'Hỏi đáp pháp luật',exact:true}).click()
    await page.getByLabel('Câu hỏi pháp luật').fill('Điều 104 Luật Đất đai 2024 quy định chi phí di chuyển tài sản gồm những khoản nào?')
    await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
    await page.locator('.message.assistant .citations button').first().waitFor({timeout:180000})
    const box=await page.locator('.composer').boundingBox()
    if(box.height>64)throw Error('Composer is not compact after real answer')
    await page.locator('.message.assistant .citations button').first().click()
    await page.getByRole('dialog',{name:'Chi tiết nguồn'}).waitFor()
    await page.keyboard.press('Escape')
    await page.locator('.message.assistant .trace-link').click()
    await page.getByRole('dialog').waitFor()
    await page.keyboard.press('Escape')
    checks.push({real_chat:true,citation_and_trace_opened:true,composer_height:box.height})
  }
  await page.screenshot({path:`reports/ui-mvp-${width}.png`,fullPage:true})
  checks.push({width,passed:true});await page.close()
 }
 await mkdir('reports/submission',{recursive:true})
 await writeFile('reports/submission/frontend-live.json',JSON.stringify({passed:true,checked_at:new Date().toISOString(),checks,scope:process.argv.includes('--chat')?'Public UI plus actual sourced LLM answer, source and trace.':'Public website UI without mocks; LLM chat checked separately.'},null,2)+'\n')
 console.log(JSON.stringify(checks))
}finally{await browser.close()}
