import asyncio,hashlib,json,io
from pathlib import Path
from datetime import datetime,timezone
import httpx
from pypdf import PdfReader
from bs4 import BeautifulSoup
base=Path('reports/phase2c-current-20261021');raw=Path('data/staging/phase2c-evidence');raw.mkdir(exist_ok=True)
(base/'source-text').mkdir(exist_ok=True)
docs=json.load(open('data/staging/production-backup-check-20261020/release.json'))['documents']
ids={'luat-dat-dai-2024','nd-88-2024','nd-226-2025','nd-49-2026','qd-40-2026-hanoi','luat-thu-do-2026','nq-258-2025','nq-90-2026-hanoi'}
targets=[]
for d in docs:
 if d['id'] in ids:
  if d['id']=='nd-88-2024':targets.append((d['id'],d['url'],None))
  for i,f in enumerate(d.get('source_files',[])):
   if d['id']=='luat-dat-dai-2024' and i!=1:continue
   targets.append((d['id']+'-'+str(i),f['url'],f['checksum']))
 if d['id']=='nq-254-2025':
  for i,f in enumerate(d['source_pages']):targets.append((d['id']+'-page-'+str(i),f['url'],f['checksum']))
targets += [('nq36-education-landing','https://ththanham.hanoi.edu.vn/van-ban-ubnd-tp-ha-noi/nghi-quyet-quy-dinh-mot-so-noi-dung-ve-cho-thue-dat-tam-nop-tien-su-dung-dat-ti/vbct/17504/1095637',None),('nq36-education-pdf','https://quantri.longbien.shieldix.app/uploadfoldernew/data/2026/ththanham/2026_7/14/ltd/nqpq-36-2026_147202614.pdf',None),('hanoi-congbao-index','https://congbao.hanoi.gov.vn/',None)]
async def main():
 sem=asyncio.Semaphore(3)
 async with httpx.AsyncClient(timeout=25,follow_redirects=True) as client:
  async def one(t):
   ident,url,expected=t
   async with sem:
    r={'id':ident,'url':url,'checked_at':datetime.now(timezone.utc).isoformat(),'method':'GET','expected_sha256':expected}
    try:
     res=await client.get(url);sha=hashlib.sha256(res.content).hexdigest();r.update(status=res.status_code,sha256=sha,bytes=len(res.content),checksum_match=sha==expected if expected else None)
     if res.status_code==200:
      suffix='.pdf' if res.content.startswith(b'%PDF') else '.jpg' if res.headers.get('content-type','').startswith('image/') else '.html'
      dest=raw/(ident+suffix);dest.write_bytes(res.content);r['raw_path']=str(dest)
      if suffix=='.pdf':text='\n'.join(f'\n[PHYSICAL PAGE {i+1}]\n'+p.extract_text() for i,p in enumerate(PdfReader(io.BytesIO(res.content)).pages))
      elif suffix=='.html':text=BeautifulSoup(res.text,'html.parser').get_text(' ',strip=True)
      else:text=''
      if text:
       path=base/'source-text'/(ident+'.txt');path.write_text(text);r['text_path']=str(path)
    except Exception as e:r['error']=type(e).__name__
    return r
  results=await asyncio.gather(*(one(t) for t in targets))
 (base/'source-access.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 for r in results:print(r['id'],r.get('status'),r.get('checksum_match'),r.get('error',''))
asyncio.run(main())
