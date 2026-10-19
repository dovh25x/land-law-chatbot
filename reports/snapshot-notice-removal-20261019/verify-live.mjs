import {chromium} from '../../frontend/node_modules/playwright/index.mjs'
import {readFile,writeFile} from 'node:fs/promises'
const directory='reports/snapshot-notice-removal-20261019',base='https://hanoi-land-law.pages.dev'
const policy=JSON.parse(await readFile(directory+'/source-policy.json','utf8')),checks=[]
const browser=await chromium.launch({headless:true})
try{
 for(const width of [1440,390,320]){
  const page=await browser.newPage({viewport:{width,height:900}})
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:90000})
  const get=async path=>{const response=await page.request.get(base+path,{timeout:90000});if(!response.ok())throw Error('Metadata HTTP '+response.status());return response.json()}
  const status=await get('/api/v1/status'),readiness=await get('/readyz'),evaluation=await get('/api/v1/evaluations/latest')
  if(!status.generation_available||status.source_fresh!==false||status.warning!=='source_stale')throw Error('Operator freshness metadata changed')
  if(readiness.corpus_release!=='corpus-a26bc99e541fbbe2')throw Error('Corpus changed')
  if(evaluation.active_configuration_sha256!==policy.configuration_sha256)throw Error('Runtime fingerprint differs')
  await page.waitForFunction(()=>!document.querySelector('.connection-note')?.textContent?.includes('Đang kết nối'),{},{timeout:90000})
  if(await page.locator('.connection-note').count())throw Error('Unexpected connection banner')
  if((await page.locator('body').innerText()).includes('Nguồn chưa được rà soát cập nhật'))throw Error('Snapshot warning remains visible')
  await page.locator('.topbar .data-trigger').click()
  const panel=page.getByLabel('Dữ liệu và phạm vi sử dụng',{exact:true});await panel.waitFor()
  if(!(await panel.innerText()).includes('Có thể sinh đáp án'))throw Error('Generation availability missing')
  if((await panel.innerText()).includes('Nguồn chưa được rà soát cập nhật'))throw Error('Snapshot warning remains in information panel')
  await page.keyboard.press('Escape')
  await page.screenshot({path:directory+'/live-'+width+'.png',fullPage:true})
  checks.push({width,snapshot_notice_visible:false,information_panel_notice_visible:false,generation_available:true,source_fresh:status.source_fresh,operator_warning:status.warning,configuration_sha256:evaluation.active_configuration_sha256})
  await page.close()
 }
 await writeFile(directory+'/live-ui.json',JSON.stringify({passed:true,checked_at:new Date().toISOString(),base,public_chat_tested:false,checks},null,2)+'\n')
 console.log(JSON.stringify({passed:true,widths:checks.map(x=>x.width)}))
}finally{await browser.close()}
