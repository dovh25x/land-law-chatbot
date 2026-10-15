// Export readable report/slides to standalone HTML and PDF using existing Playwright.
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
const escape = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')
const browser = await chromium.launch({headless:true})
try {
 for (const [source,name,slides] of [['docs/submission/REPORT.md','report',false],['docs/submission/SLIDES.md','slides',true]]) {
  let text = await readFile(source,'utf8')
  if (!slides) {
   try { text += '\n\n'+await readFile('reports/submission/results.md','utf8') } catch {}
  }
  const parts = slides ? text.split(/^## /m).slice(1).map(s=>'## '+s) : [text]
  const body = parts.map(part=>'<section>'+part.split('\n').map(line=>{
   const m=line.match(/^(#{1,3}) (.*)$/)
   return m?`<h${m[1].length}>${escape(m[2])}</h${m[1].length}>`:`<div class="line">${escape(line)||'&nbsp;'}</div>`
  }).join('\n')+'</section>').join('\n')
  const html=`<!doctype html><html lang="vi"><meta charset="utf-8"><title>Hanoi Land Law — ${name}</title><style>body{font:15px/1.65 Arial,sans-serif;color:#172e35;margin:36px auto;max-width:1000px;padding:24px}h1,h2,h3{color:#0c6761}.line{white-space:pre-wrap;overflow-wrap:anywhere}section{margin-bottom:30px}${slides?'section{break-after:page;min-height:540px;font-size:23px}h2{font-size:38px}':'h2,h3{break-after:avoid}.line{font-size:12px}' }@media print{body{margin:0;padding:0}section:last-child{break-after:auto}}</style>${body}</html>`
  await writeFile(`docs/submission/${name}.html`,html)
  const page=await browser.newPage();await page.setContent(html)
  await page.pdf({path:`docs/submission/${name}.pdf`,format:'A4',landscape:slides,printBackground:true,margin:{top:'15mm',bottom:'15mm',left:'15mm',right:'15mm'}})
  await page.close()
 }
} finally {await browser.close()}
console.log('Exported report and 10-slide HTML/PDF; source Markdown remains editable.')
