import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { writeFile } from 'node:fs/promises'
const base='https://hanoi-land-law.pages.dev', checks=[]
const browser=await chromium.launch({headless:true})
try {
 for (const width of [1440,390,320]) {
  const page=await browser.newPage({viewport:{width,height:900}})
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:90000})
  const get=async path=>{const r=await page.request.get(base+path,{timeout:90000});if(!r.ok())throw Error('Metadata HTTP '+r.status());return r.json()}
  const library=await get('/api/v1/documents'),status=await get('/api/v1/status'),ready=await get('/readyz')
  if(library.documents.length!==60||library.references.length!==8)throw Error('Unexpected library composition')
  if(!status.generation_available||status.warning!=='source_stale'||ready.corpus_release!=='corpus-a26bc99e541fbbe2')throw Error('Runtime mode differs')
  const menu=page.getByRole('button',{name:'Mở menu điều hướng'});if(await menu.isVisible())await menu.click()
  await page.getByRole('button',{name:'Thư viện văn bản',exact:true}).click()
  await page.getByLabel('Tìm văn bản').fill('boi thuong')
  await page.locator('.document-row').first().waitFor({timeout:90000})
  const accentMatches=await page.locator('.document-row').count()
  await page.getByLabel('Tìm văn bản').fill('281/2026')
  await page.locator('.document-row').click()
  await page.locator('.source-card').filter({hasText:'không được dùng làm căn cứ'}).waitFor()
  const original=await page.getByRole('link',{name:'Mở bản gốc 1'}).getAttribute('href')
  if(!original?.startsWith('https://datafiles.chinhphu.vn/'))throw Error('Unexpected original provenance')
  const doc=await get('/api/v1/documents/nd-281-2026')
  if(doc.document.chunks.length||doc.document.availability!=='reference_only')throw Error('Reference became AI evidence')
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Horizontal overflow')
  checks.push({width,indexed:library.documents.length,references:library.references.length,accent_free_matches:accentMatches,official_original:original,reference_excluded_from_evidence:true,generation_available:status.generation_available,source_fresh:status.source_fresh})
  await page.close()
 }
 await writeFile('reports/product-completion-20261019/product-live.json',JSON.stringify({passed:true,checked_at:new Date().toISOString(),base,checks},null,2)+'\n')
 console.log(JSON.stringify({passed:true,widths:checks.map(x=>x.width)}))
}finally{await browser.close()}
