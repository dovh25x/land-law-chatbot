import asyncio,hashlib,io,json
from datetime import datetime,timezone
from pathlib import Path
import httpx
from pypdf import PdfReader
urls={'vbhn44':'https://congbaocdn.chinhphu.vn/180507251028987904/2026/4/1/cong-bao-so-174-ngay-01-04-47090_1775005842_signed.pdf','vbhn53':'https://xdcs.cdnchinhphu.vn/446259493575335936/2026/5/19/53-vbhn-bnnmt-17791831327852120266934.pdf'}
async def main():
 results=[]
 async with httpx.AsyncClient(timeout=30,follow_redirects=True) as c:
  for ident,url in urls.items():
   row={'id':ident,'url':url,'checked_at':datetime.now(timezone.utc).isoformat()}
   try:
    r=await c.get(url);r.raise_for_status();row.update(status=r.status_code,sha256=hashlib.sha256(r.content).hexdigest())
    p=Path('data/staging/phase2c-evidence')/(ident+'.pdf');p.write_bytes(r.content)
    text='\n'.join(f'\n[PHYSICAL PAGE {i+1}]\n'+p.extract_text() for i,p in enumerate(PdfReader(io.BytesIO(r.content)).pages))
    f=Path('reports/phase2c-current-20261021/source-text')/(ident+'.txt');f.write_text(text);row['text_path']=str(f)
   except Exception as e:row['error']=type(e).__name__
   results.append(row)
 Path('reports/phase2c-current-20261021/consolidated-access.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results))
asyncio.run(main())
