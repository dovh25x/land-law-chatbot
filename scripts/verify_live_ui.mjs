// Real public UI; no API interception. Source-only mode never certifies LLM generation.
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { writeFile, mkdir, readFile } from 'node:fs/promises'
const sourceOnly=process.argv.includes('--source-only')
const chat=process.argv.includes('--chat')||sourceOnly
const output=!chat?'reports/frontend-live-ui.json':sourceOnly?'reports/frontend-live.json':'reports/frontend-live-generation.json'
const api='https://land-law-chatbot.onrender.com'
const browser=await chromium.launch({headless:true})
const checks=[]
let phase='navigation'
const scope=!chat?'Public website UI only; chat and generation are not checked.':sourceOnly?'Actual public UI, sourced deterministic chat, same-session follow-up, trace authorization and restoration. LLM generation is NOT verified.':'Actual public UI and sourced LLM chat with follow-up, trace authorization and restoration.'
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
  if(width===1440 && chat) {
    phase='configuration'
    const live=await (await page.request.get(api+'/api/v1/evaluations/latest')).json()
    const expected=JSON.parse(await readFile('reports/latest.json','utf8'))
    if(!live.matches_active_configuration || !live.matches_active_release || live.active_configuration_sha256!==expected.configuration_sha256)throw Error('Runtime/report mismatch')
    await page.getByRole('button',{name:'Đánh giá hệ thống',exact:true}).click()
    await page.locator('.evaluation-table').last().locator('tbody tr').last().waitFor()
    if(await page.locator('.evaluation-table').last().locator('tbody tr').count()!==20)throw Error('Twenty-case table missing')
    await page.getByText('Kiểm tra bổ sung',{exact:true}).waitFor()
    checks.push({reviewed_evaluation_rows:20,supplemental_visible:true,configuration_sha256:live.active_configuration_sha256})
    await page.getByRole('button',{name:'Hỏi đáp pháp luật',exact:true}).click()
    async function submit(question) {
      const pending=page.waitForResponse(r=>r.request().method()==='POST' && r.url().endsWith('/api/v1/chat'),{timeout:180000})
      await page.getByLabel('Câu hỏi pháp luật').fill(question)
      await page.getByRole('button',{name:'Gửi câu hỏi'}).click()
      const response=await pending
      if(!response.ok())throw Error('Chat HTTP failed')
      const frames=(await response.text()).split('\n').filter(line=>line.startsWith('data: ')).map(line=>JSON.parse(line.slice(6)))
      const result=frames.find(frame=>frame.trace_id)
      if(!result || result.status!=='answered' || !result.citations?.length)throw Error('No sourced answer')
      if(sourceOnly && result.llm_calls!==0)throw Error('Source-only probe unexpectedly used LLM')
      return {result,sessionId:response.request().postDataJSON().session_id}
    }
    phase='first_chat'
    const first=await submit(sourceOnly?'Quyết định 56/2024/QĐ-UBND Hà Nội còn hiệu lực không? Văn bản nào thay thế?':'Điều 104 Luật Đất đai 2024 quy định chi phí di chuyển tài sản gồm những khoản nào?')
    if(!sourceOnly && !first.result.llm_calls)throw Error('No actual LLM generation')
    await page.locator('.message.assistant .citations button').first().click()
    await page.getByRole('dialog',{name:'Chi tiết nguồn'}).waitFor()
    await page.keyboard.press('Escape')
    await page.locator('.message.assistant .trace-link').first().click()
    await page.getByRole('dialog',{name:'Quá trình kiểm chứng'}).waitFor()
    await page.keyboard.press('Escape')
    phase='followup'
    const second=await submit(sourceOnly?'Văn bản đó thay thế Quyết định 56/2024/QĐ-UBND từ ngày nào?':'Văn bản đó quy định cơ quan nào quyết định mức bồi thường tại Điều 104?')
    if(second.sessionId!==first.sessionId)throw Error('Follow-up switched sessions')
    phase='trace_authorization'
    // Credentials stay in process memory; only boolean checks are written.
    const session=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('landlaw-session')))
    const traceURL=api+`/api/v1/sessions/${session.session_id}/traces/${second.result.trace_id}`
    const allowed=await page.request.get(traceURL,{headers:{Authorization:'Bearer '+session.token}})
    const denied=await page.request.get(traceURL,{headers:{Authorization:'Bearer invalid'}})
    if(allowed.status()!==200 || ![401,404].includes(denied.status()))throw Error('Trace isolation failed')
    phase='restoration'
    await page.reload({waitUntil:'networkidle'})
    await page.locator('.message.assistant').nth(1).waitFor()
    if(await page.locator('.message.assistant').count()!==2)throw Error('Conversation restoration failed')
    const box=await page.locator('.composer').boundingBox()
    if(box.height>64)throw Error('Composer is not compact')
    checks.push({real_chat:true,source_only:sourceOnly,llm_calls:[first.result.llm_calls,second.result.llm_calls],same_session_followup:true,trace_access_isolated:true,restored_messages:4,composer_height:box.height})
  }
  phase='responsive'
  await page.screenshot({path:`reports/ui-live-${width}.png`,fullPage:true})
  checks.push({width,passed:true});await page.close()
 }
 await mkdir('reports',{recursive:true})
 await writeFile(output,JSON.stringify({passed:true,checked_at:new Date().toISOString(),checks,llm_generation_checked:chat&&!sourceOnly,scope},null,2)+'\n')
 console.log(JSON.stringify({passed:true,llm_generation_checked:chat&&!sourceOnly,checks}))
}catch(error){
 await mkdir('reports',{recursive:true})
 await writeFile(output,JSON.stringify({passed:false,checked_at:new Date().toISOString(),phase,error_type:error.constructor.name,checks,llm_generation_checked:false,scope},null,2)+'\n')
 throw Error(`Live UI verification failed at ${phase}; see ${output}`)
}finally{await browser.close()}
