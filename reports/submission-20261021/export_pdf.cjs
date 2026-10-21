// Offline HTML export. Block all non-file network requests, including SVG web fonts.
const { chromium } = require('../../frontend/node_modules/playwright');
const path = require('node:path');
const fs = require('node:fs');
(async () => {
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
 await page.route(/https?:\/\//, route=>route.abort());
 await page.goto('file://'+path.join(__dirname,'../../docs/diagrams/architecture.svg'));
 await page.locator('svg').screenshot({path:path.join(__dirname,'architecture.png')});
 if(process.argv.includes('--prepare-assets-only')) { await browser.close(); console.log('Architecture raster prepared from existing SVG.'); return; }
 const checks={};
 for (const file of ['Final_Project_Report','Final_Project_Presentation']) {
  await page.goto('file://'+path.join(__dirname,file+'.html'),{waitUntil:'load'});
  await page.evaluate(()=>document.fonts.ready);
  if(file.endsWith('Presentation')) {
   checks.slide_layout=await page.locator('.slide').evaluateAll(nodes=>nodes.map(n=>({slide:n.dataset.slide,scrollWidth:n.scrollWidth,clientWidth:n.clientWidth,scrollHeight:n.scrollHeight,clientHeight:n.clientHeight,content_overflow:[...n.querySelectorAll('h1,.lead,.cards,.metric-row,.card-desc')].filter(e=>{const r=e.getBoundingClientRect(),p=n.getBoundingClientRect();return r.right>p.right||r.bottom>p.bottom-50||e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2}).map(e=>e.className||e.tagName)})));
   await page.locator('.slide').first().screenshot({path:path.join(__dirname,'preview-slide-01.png')});
   await page.locator('.slide').nth(8).screenshot({path:path.join(__dirname,'preview-slide-09.png')});
  }
  await page.pdf({path:path.join(__dirname,file+'.pdf'),preferCSSPageSize:true,printBackground:true,displayHeaderFooter:file.endsWith('Report'),headerTemplate:'<span></span>',footerTemplate:'<div style="font-size:8px;color:#60717b;width:100%;text-align:center;font-family:Arial">Hanoi Land Law Assistant · 21/10/2026 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
 }
 fs.writeFileSync(path.join(__dirname,'layout-check.json'),JSON.stringify(checks,null,2)+'\n');
 await browser.close();
 console.log('PDFs exported offline.');
})().catch(e=>{console.error(e.message);process.exitCode=1});
