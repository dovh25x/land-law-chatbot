import {chromium} from '../../frontend/node_modules/playwright/index.mjs'
import {writeFile} from 'node:fs/promises'
const directory='reports/evaluation-highlights-20261019',base='https://hanoi-land-law.pages.dev',checks=[]
const browser=await chromium.launch({headless:true})
try{
 for(const width of [1440,390,320]){
  const page=await browser.newPage({viewport:{width,height:960}})
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:90000})
  const response=await page.request.get(base+'/api/v1/evaluations/latest',{timeout:90000});if(!response.ok())throw Error('Evaluation API unavailable')
  const data=await response.json()
  const menu=page.getByRole('button',{name:'Mở menu điều hướng'});if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'Đánh giá hệ thống',exact:true}).click()
  const cards=page.getByRole('region',{name:'Kết quả nổi bật đã ghi nhận'})
  await cards.waitFor({timeout:90000})
  const expected=[['smoke','95%','19/20 ca đạt đủ tiêu chí'],['recall','100%','3 ca có gold · Bộ bổ sung'],['faithfulness','92,3%','6/8 ca có điểm · 13 mệnh đề']]
  for(const [metric,value,sample]of expected){
   const card=cards.locator('[data-metric="'+metric+'"]')
   if(await card.locator('.eval-highlight-value').innerText()!==value)throw Error('Record value differs: '+metric)
   if(!(await card.innerText()).includes(sample))throw Error('Record sample missing: '+metric)
   const href=await card.getByRole('link',{name:'Xem phép đo gốc'}).getAttribute('href')
   if(!href?.startsWith('https://github.com/dovh25x/land-law-chatbot/blob/'))throw Error('Record provenance missing')
  }
  if(!(await cards.locator('[data-metric="smoke"]').innerText()).includes('Kết quả lịch sử · corpus khác'))throw Error('Historical score presented as current')
  if(await page.getByLabel('Lần đánh giá',{exact:true}).inputValue()!==data.default_run_id)throw Error('Default run changed')
  if(await page.locator('.stat-pass strong').innerText()!=='22/32'||await page.locator('.stat-fail strong').innerText()!=='7')throw Error('Current results hidden or modified')
  await page.locator('.evaluation-page').evaluate(el=>{el.scrollTop=0})
  await page.screenshot({path:directory+'/live-'+width+'.png'})
  await page.getByRole('button',{name:'Xem toàn bộ kết quả và các ca chưa đạt'}).click()
  await page.getByLabel('Lọc kết quả',{exact:true}).selectOption('fail')
  if(await page.locator('.eval-case').count()!==7)throw Error('Failed cases unavailable')
  if(data.runs.length!==13||data.sources.length!==63)throw Error('Archive coverage changed')
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow')
  checks.push({width,records:['95% · 19/20 smoke','100% · 3 supplemental retrieval cases','92.3% · 6/8 scored cases, 13 claims'],historical_scope_visible:true,selected_run_unchanged:true,all_failed_cases_available:7,generation_runs:13,artifacts:63})
  await page.close()
 }
 await writeFile(directory+'/live-ui.json',JSON.stringify({passed:true,checked_at:new Date().toISOString(),base,public_chat_tested:false,checks},null,2)+'\n')
 console.log(JSON.stringify({passed:true,widths:checks.map(x=>x.width)}))
}finally{await browser.close()}
