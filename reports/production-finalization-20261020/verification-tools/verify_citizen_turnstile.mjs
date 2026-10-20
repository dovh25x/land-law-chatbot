import {chromium} from '/home/dovh25x/projects/land-law-chatbot/frontend/node_modules/playwright/index.mjs'
import {writeFile} from 'node:fs/promises'
const base='https://hanoi-land-law.pages.dev',output='reports/production-finalization-20261020/live-turnstile.json'
let browser,phase='load',tokenObserved=false,sessionVerified=false
try {
 browser=await chromium.launch({headless:true})
 const page=await browser.newPage({viewport:{width:1440,height:900}})
 await page.goto(base,{waitUntil:'domcontentloaded',timeout:90000})
 await page.getByLabel('Câu hỏi pháp luật').waitFor()
 phase='managed_challenge'
 await page.waitForFunction(()=>!!document.querySelector('input[name="cf-turnstile-response"]')?.value,{}, {timeout:45000})
 const token=await page.locator('input[name="cf-turnstile-response"]').inputValue();tokenObserved=true
 phase='session_verification'
 const response=await page.request.post(base+'/api/v1/sessions',{data:{turnstile_token:token},timeout:20000})
 if(response.status()!==201)throw Error('Session verification HTTP '+response.status())
 const session=await response.json();sessionVerified=true
 const valid=await page.request.get(base+'/api/v1/sessions/'+session.session_id,{headers:{Authorization:'Bearer '+session.token}})
 const denied=await page.request.get(base+'/api/v1/sessions/'+session.session_id,{headers:{Authorization:'Bearer invalid'}})
 const retired=await page.request.get(base+'/api/v1/sessions/'+session.session_id+'/messages',{headers:{Authorization:'Bearer '+session.token}})
 if(valid.status()!==200||denied.status()!==404||retired.status()!==410)throw Error('Session isolation or retired history failed')
 await writeFile(output,JSON.stringify({passed:true,checked_at:new Date().toISOString(),base_url:base,real_managed_turnstile:true,token_observed:true,session_verified:true,authenticated_session_http:200,invalid_session_http:404,retired_history_http:410,conversation_submitted:false,llm_generation_checked:false,scope:'Real browser token and public HTTPS session; no challenge automation, test key or conversation payload persisted.'},null,2)+'\n')
 console.log(JSON.stringify({passed:true,output}))
} catch(error) {
 const safe=phase==='managed_challenge'?'Managed Turnstile did not produce a token; human interaction may be required.':error.message
 await writeFile(output,JSON.stringify({passed:false,checked_at:new Date().toISOString(),phase,error:safe,token_observed:tokenObserved,session_verified:sessionVerified,llm_generation_checked:false,conversation_submitted:false,scope:'No bypass, test token or automated checkbox; live chat generation remains unverified under provider quota.'},null,2)+'\n')
 console.log(JSON.stringify({passed:false,phase,error:safe,output}));process.exitCode=1
} finally {await browser?.close()}
