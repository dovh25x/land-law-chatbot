import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import {readFile,writeFile} from 'node:fs/promises'
const directory='reports/evaluation-dashboard-20261019',base='https://hanoi-land-law.pages.dev'
const expected=JSON.parse(await readFile(directory+'/runtime-identity.json','utf8')).configuration_sha256
const browser=await chromium.launch({headless:true}),checks=[]
try{
 for(const width of [1440,390,320]){
  const page=await browser.newPage({viewport:{width,height:960}})
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:90000})
  const response=await page.request.get(base+'/api/v1/evaluations/latest',{timeout:90000});if(!response.ok())throw Error('Report API unavailable')
  const data=await response.json(),full=data.runs?.find(r=>r.configuration_sha256?.startsWith('8db2d701')),probe=data.runs?.find(r=>r.configuration_sha256?.startsWith('380801c7'))
  if(data.active_configuration_sha256!==expected)throw Error('Runtime fingerprint differs')
  if(data.sources.length!==63||data.runs.length!==13||data.retrieval_runs.length!==35||data.faithfulness_runs.length!==2)throw Error('Evaluation coverage differs')
  if(data.default_run_id!==full.id)throw Error('Unexpected default run')
  const menu=page.getByRole('button',{name:'Mở menu điều hướng'});if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'Đánh giá hệ thống',exact:true}).click()
  await page.waitForFunction(()=>document.querySelector('.stat-pass strong')?.textContent==='22/32',{},{timeout:90000})
  if((await page.locator('.stat-fail strong').innerText())!=='7')throw Error('Failed cases hidden')
  await page.locator('.evaluation-page').evaluate(element=>{element.scrollTop=0})
  await page.screenshot({path:directory+'/live-overview-'+width+'.png'})
  await page.locator('.eval-suite-grid').screenshot({path:directory+'/live-suites-'+width+'.png'})
  await page.getByLabel('Lọc kết quả',{exact:true}).selectOption('fail')
  if(await page.locator('.eval-case').count()!==7)throw Error('Failure filter mismatch')
  await page.getByLabel('Tìm ca đánh giá').fill('N02');await page.locator('.eval-case summary').click()
  if(!(await page.locator('.eval-case-body').innerText()).includes('khoản 2 Điều 19'))throw Error('Review note missing')
  await page.getByLabel('Lần đánh giá',{exact:true}).selectOption(probe.id)
  if((await page.locator('.stat-not_run strong').innerText())!=='7')throw Error('Unexecuted cases hidden')
  await page.getByLabel('Lần đánh giá',{exact:true}).selectOption(full.id)
  await page.getByRole('button',{name:'Tìm nguồn & đối chiếu',exact:true}).click()
  if(await page.locator('.eval-faith-card').count()!==2)throw Error('Faithfulness history missing')
  await page.getByRole('checkbox',{name:/Hiện tất cả phiên bản/}).check()
  if(await page.locator('.evaluation-table tbody tr').count()!==35)throw Error('Retrieval history incomplete')
  await page.getByRole('button',{name:'Lịch sử đánh giá',exact:true}).click()
  if(await page.locator('.eval-history-row').count()!==13)throw Error('Generation history incomplete')
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Page overflows horizontally')
  checks.push({width,generation_runs:13,retrieval_reports:35,faithfulness_reports:2,artifacts:63,pass:22,partial:3,fail:7,expected_cases:32,natural_content_pass:2,natural_content_cases:6,incomplete_probe_unexecuted:7,filter_review_and_history_checked:true})
  await page.close()
 }
 await writeFile(directory+'/live-ui.json',JSON.stringify({passed:true,checked_at:new Date().toISOString(),base,configuration_sha256:expected,public_chat_tested:false,checks},null,2)+'\n')
 console.log(JSON.stringify({passed:true,widths:checks.map(x=>x.width)}))
}finally{await browser.close()}
