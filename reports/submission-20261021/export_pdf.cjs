// Offline HTML export. Block all non-file network requests, including SVG web fonts.
const { chromium } = require('../../frontend/node_modules/playwright');
const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
(async () => {
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
 await page.route(/https?:\/\//, route=>route.abort());
 await page.goto('file://'+path.join(__dirname,'../../docs/diagrams/architecture.svg'));
 await page.locator('svg').screenshot({path:path.join(__dirname,'architecture.png')});
 if(process.argv.includes('--prepare-assets-only')) { await browser.close(); console.log('Architecture raster prepared from existing SVG.'); return; }
 const identityPath=path.join(__dirname,'build-source-identity.json');
 const identity=JSON.parse(fs.readFileSync(identityPath,'utf8'));
 for(const [name,sha] of Object.entries({...identity.inputs_sha256,...identity.generated_sha256})) {
  if(digest(fs.readFileSync(path.join(__dirname,name)))!==sha) throw new Error('Build source changed; rebuild before export: '+name);
 }
 const checks={};
 for (const file of ['Final_Project_Report','Final_Project_Presentation']) {
  await page.goto('file://'+path.join(__dirname,file+'.html'),{waitUntil:'load'});
  await page.evaluate(()=>document.fonts.ready);
  // Only anchors become public URLs. Images/SVGs stay local for offline rendering.
  checks[file+'_links']=await page.evaluate(({root,tag,source})=>{
   const repo='https://github.com/dovh25x/land-law-chatbot';
   const result={repository_anchors:0,binary_anchors:0,internal_fragments:0};
   for(const anchor of document.querySelectorAll('a[href]')) {
    const raw=anchor.getAttribute('href');
    if(raw.startsWith('#')) {
     const original=decodeURIComponent(raw.slice(1));
     const normalized=original.normalize('NFKD').replace(/\p{Diacritic}/gu,'').replace(/đ/g,'d');
     const destination=document.getElementById(original)||document.getElementById(normalized);
     if(destination) {anchor.setAttribute('href','#'+destination.id);result.internal_fragments++;continue;}
     anchor.href=repo+'/blob/'+tag+'/'+source+raw;result.repository_anchors++;continue;
    }
    const target=new URL(raw,document.baseURI);
    if(target.protocol!=='file:') continue;
    const localPath=decodeURIComponent(target.pathname);
    if(!localPath.startsWith(root+'/')) throw new Error('Anchor outside repository: '+raw);
    const relative=localPath.slice(root.length+1);
    if(/\.(pdf|pptx|zip)$/i.test(relative)) {
     anchor.href=repo+'/releases/download/'+tag+'/'+encodeURIComponent(relative.split('/').pop());
     result.binary_anchors++;
    } else {
     anchor.href=repo+'/blob/'+tag+'/'+relative.split('/').map(encodeURIComponent).join('/')+target.hash;
     result.repository_anchors++;
    }
   }
   return result;
  },{root:path.resolve(__dirname,'../..'),tag:'v0.1.0-academic-20261021',source:'reports/submission-20261021/Final_Project_Report.md'});
  if(file.endsWith('Presentation')) {
   checks.slide_layout=await page.locator('.slide').evaluateAll(nodes=>nodes.map(n=>({slide:n.dataset.slide,scrollWidth:n.scrollWidth,clientWidth:n.clientWidth,scrollHeight:n.scrollHeight,clientHeight:n.clientHeight,content_overflow:[...n.querySelectorAll('h1,.lead,.cards,.metric-row,.card-desc')].filter(e=>{const r=e.getBoundingClientRect(),p=n.getBoundingClientRect();return r.right>p.right||r.bottom>p.bottom-50||e.scrollHeight>e.clientHeight+2||e.scrollWidth>e.clientWidth+2}).map(e=>e.className||e.tagName)})));
   await page.locator('.slide').first().screenshot({path:path.join(__dirname,'preview-slide-01.png')});
   await page.locator('.slide').nth(8).screenshot({path:path.join(__dirname,'preview-slide-09.png')});
  }
  await page.pdf({path:path.join(__dirname,file+'.pdf'),preferCSSPageSize:true,printBackground:true,displayHeaderFooter:file.endsWith('Report'),headerTemplate:'<span></span>',footerTemplate:'<div style="font-size:8px;color:#60717b;width:100%;text-align:center;font-family:Arial">Hanoi Land Law Assistant · 21/10/2026 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
 }
 fs.writeFileSync(path.join(__dirname,'layout-check.json'),JSON.stringify(checks,null,2)+'\n');
 fs.writeFileSync(path.join(__dirname,'export-identity.json'),JSON.stringify({build_source_identity_sha256:digest(fs.readFileSync(identityPath)),pdf_sha256:Object.fromEntries(['Final_Project_Report.pdf','Final_Project_Presentation.pdf'].map(name=>[name,digest(fs.readFileSync(path.join(__dirname,name)))])),scope:'Offline Chromium export; not model or deployment validation'},null,2)+'\n');
 await browser.close();
 console.log('PDFs exported offline.');
})().catch(e=>{console.error(e.message);process.exitCode=1});
