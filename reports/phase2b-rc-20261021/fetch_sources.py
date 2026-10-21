import asyncio,hashlib,json,time
from pathlib import Path
from datetime import datetime,timezone
import httpx,io
from pypdf import PdfReader
from bs4 import BeautifulSoup
base=Path('reports/phase2b-rc-20261021');(base/'source-text').mkdir(exist_ok=True)
p=json.load(open('data/staging/production-backup-check-20261020/release.json'))
ids={'luat-dat-dai-2024','luat-43-2024','nd-88-2024','nd-151-2025','nd-226-2025','nd-49-2026','qd-40-2026-hanoi','qd-38-2025-hanoi','qd-10-2026-hanoi'}
targets=[]
for d in p['documents']:
 if d['id'] not in ids:continue
 targets.append((d['id']+'-landing',d['url'],None))
 for i,f in enumerate(d.get('source_files',[])):
  if d['id']=='nd-151-2025' and i>0:continue
  if d['id']=='luat-dat-dai-2024' and i!=1:continue
  targets.append((d['id']+'-pdf-'+str(i),f['url'],f['checksum']))
targets.extend([('qd40-registry','https://vbpl.moj.gov.vn/hanoi/pages/vbpq-thuoctinh.aspx?ItemID=187625&dvid=305',None),('qd40-relations','https://congbao.hanoi.gov.vn/Default.aspx?p_diagram=5335&pageid=45001',None)])
async def main():
 sem=asyncio.Semaphore(2)
 async with httpx.AsyncClient(timeout=25,follow_redirects=True) as client:
  async def one(t):
   ident,url,expected=t
   async with sem:
    r={'id':ident,'url':url,'checked_at':datetime.now(timezone.utc).isoformat(),'method':'GET'};start=time.monotonic()
    try:
     res=await client.get(url);r.update(status=res.status_code,sha256=hashlib.sha256(res.content).hexdigest(),bytes=len(res.content),expected_sha256=expected,checksum_match=(hashlib.sha256(res.content).hexdigest()==expected) if expected else None)
     if res.status_code==200:
      if res.content.startswith(b'%PDF'):
       doc=PdfReader(io.BytesIO(res.content));text='\n'.join(f'\n[PHYSICAL PAGE {i+1}]\n'+page.extract_text() for i,page in enumerate(doc.pages))
      else:text=BeautifulSoup(res.text,'html.parser').get_text(' ',strip=True)
      path=base/'source-text'/(ident+'.txt');path.write_text(text);r['text_path']=str(path)
    except Exception as exc:r['error']=type(exc).__name__
    r['elapsed_ms']=round((time.monotonic()-start)*1000);return r
  results=await asyncio.gather(*(one(t) for t in targets))
 (base/'source-access.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps([{k:r.get(k) for k in ('id','status','checksum_match','error')} for r in results]))
asyncio.run(main())
