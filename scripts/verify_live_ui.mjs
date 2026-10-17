// Real deployed browser checks. No route interception, mocked challenge or server history.
import {chromium} from '../frontend/node_modules/playwright/index.mjs'
import {writeFile,mkdir} from 'node:fs/promises'
import {spawnSync} from 'node:child_process'
const chat=process.argv.includes('--chat'),sourceOnly=process.argv.includes('--source-only')
const base=process.env.LIVE_BASE_URL||'https://hanoi-land-law.pages.dev'
const output=chat?(sourceOnly?'reports/frontend-live-source-only.json':'reports/frontend-live-generation.json'):'reports/frontend-live-ui.json'
const checks=[];let phase='navigation',browser,turnstileChecked=false
const local=spawnSync('.venv/bin/python',['-c','from landlaw.config import Settings; from landlaw.evaluation import configuration_fingerprint; print(configuration_fingerprint(Settings()))'],{encoding:'utf8'})
const expected=local.status===0?local.stdout.trim():null
const browserHistory=page=>page.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('landlaw-history',1);r.onsuccess=()=>{const db=r.result;const tx=db.transaction('conversations');const q=tx.objectStore('conversations').getAll();q.onsuccess=()=>resolve(q.result);q.onerror=()=>reject(Error('Local history unavailable'));tx.oncomplete=()=>db.close()};r.onerror=()=>reject(Error('IndexedDB unavailable'))}))
const menu=async page=>{const opener=page.getByRole('button',{name:'Mở menu điều hướng'});if(await opener.isVisible())await opener.click()}
try{
 browser=await chromium.launch({headless:true})
 for(const width of [1440,390,320]){
  const page=await browser.newPage({viewport:{width,height:900}})
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:60000})
  await page.getByLabel('Câu hỏi pháp luật').waitFor()
  if(await page.getByLabel('Dự án',{exact:true}).count()||await page.getByLabel('Chế độ truy xuất').count())throw Error('Unexpected scope/model controls')
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow')
  await menu(page);await page.getByRole('button',{name:'Thư viện văn bản',exact:true}).click()
  await page.locator('.document-row').first().waitFor({timeout:90000})
  const docs=await (await page.request.get(base+'/api/v1/documents')).json()
  if(docs.documents.length!==59||docs.documents.some(d=>d.project&&d.project!=='ring4'))throw Error('Corpus scope/count differs')
  await page.locator('.document-row').first().click();await page.getByRole('dialog',{name:'Chi tiết nguồn'}).waitFor();await page.keyboard.press('Escape')
  await menu(page);await page.getByRole('button',{name:'Hỏi đáp pháp luật',exact:true}).click()
  if(width===1440&&chat){
   phase='configuration'
   const live=await(await page.request.get(base+'/api/v1/evaluations/latest')).json()
   if(expected&&live.active_configuration_sha256!==expected)throw Error('Deployed fingerprint differs from tested source')
   checks.push({runtime_configuration_sha256:live.active_configuration_sha256,report_matches_configuration:live.matches_active_configuration,report_matches_corpus:live.matches_active_release})
   phase='turnstile'
   await page.waitForFunction(()=>!!document.querySelector('input[name="cf-turnstile-response"]')?.value,{},{timeout:45000})
   turnstileChecked=true
   async function submit(question){
    const previous=await page.locator('.message.assistant').count()
    const pending=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/v1/chat'),{timeout:110000})
    await page.getByLabel('Câu hỏi pháp luật').fill(question);await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
    const response=await pending;if(!response.ok())throw Error('Chat HTTP '+response.status())
    await page.locator('.message.assistant').nth(previous).waitFor({timeout:110000})
    const rows=await browserHistory(page);const latest=rows.sort((a,b)=>b.updated_at-a.updated_at)[0]
    const result=latest.messages.filter(m=>m.role==='assistant').at(-1)?.result
    if(!result||result.status!=='answered'||!result.citations.length)throw Error('No completed source-backed answer')
    return {result,payload:response.request().postDataJSON()}
   }
   phase='generation'
   const first=await submit(sourceOnly?'Quyết định 56/2024/QĐ-UBND Hà Nội còn hiệu lực không? Văn bản nào thay thế?':'Chi phí di chuyển tài sản khi bị thu hồi đất được quy định như thế nào?')
   if(sourceOnly?first.result.llm_calls!==0:first.result.llm_calls<1)throw Error('Unexpected generation origin')
   await page.locator('.message.assistant .citations button').first().click();await page.getByRole('dialog',{name:'Chi tiết nguồn'}).waitFor();await page.keyboard.press('Escape')
   await page.locator('.message.assistant .trace-link').first().click();await page.getByRole('dialog',{name:'Quá trình kiểm chứng'}).waitFor();await page.keyboard.press('Escape')
   phase='follow_up'
   const second=await submit('Văn bản đó quy định cơ quan nào quyết định mức bồi thường chi phí di chuyển tài sản?')
   if(second.payload.history.length<2||second.payload.session_id!==first.payload.session_id)throw Error('Follow-up context/session missing')
   const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('landlaw-session')))
   const forbidden=await page.request.get(base+'/api/v1/sessions/'+session.session_id,{headers:{Authorization:'Bearer invalid'}})
   if(forbidden.status()!==404)throw Error('Session isolation failed')
   const retired=await page.request.get(base+'/api/v1/sessions/'+session.session_id+'/messages',{headers:{Authorization:'Bearer '+session.token}})
   if(retired.status()!==410)throw Error('Server history endpoint not retired')
   phase='reload_and_delete';await page.reload();await page.locator('.message.assistant').nth(1).waitFor()
   page.on('dialog',d=>d.accept());await menu(page);await page.getByRole('button',{name:'Xóa toàn bộ lịch sử'}).click()
   await page.waitForFunction(()=>document.querySelectorAll('.history-row').length===0)
   if((await browserHistory(page)).length)throw Error('Local history not cleared')
   checks.push({llm_generation_checked:!sourceOnly,first_llm_calls:first.result.llm_calls,follow_up_history:second.payload.history.length,client_sources_and_trace:true,reload:true,delete:true,server_history_410:true,session_isolation:true})
  }
  await page.screenshot({path:`reports/live-ring4-${width}.png`,fullPage:true})
  checks.push({width,corpus_documents:59,responsive:true});await page.close()
 }
 await mkdir('reports',{recursive:true});await writeFile(output,JSON.stringify({passed:true,checked_at:new Date().toISOString(),base_url:base,llm_generation_checked:chat&&!sourceOnly,turnstile_browser_checked:turnstileChecked,checks},null,2)+'\n')
 console.log(JSON.stringify({passed:true,output,llm_generation_checked:chat&&!sourceOnly}))
}catch(e){await mkdir('reports',{recursive:true});await writeFile(output,JSON.stringify({passed:false,checked_at:new Date().toISOString(),base_url:base,phase,error:e.message,llm_generation_checked:false,turnstile_browser_checked:turnstileChecked,checks},null,2)+'\n');console.log(JSON.stringify({passed:false,phase,error:e.message,output}));process.exitCode=1}
finally{await browser?.close()}
