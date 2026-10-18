import asyncio,json
from pathlib import Path
import httpx
from landlaw.security import digest
from pypdf import PdfReader
async def main():
 url='https://storage-vnportal.vnpt.vn/gov-hni/CrawlDownloads/vanban-hanoi-gov-vn/documents/10182/2518750/QDPQ-20-2022.pdf'
 async with httpx.AsyncClient(timeout=30,follow_redirects=True) as c:
  r=await c.get(url);row={'url':url,'status':r.status_code,'pdf':r.content.startswith(b'%PDF')}
  if row['pdf']:
   path=Path('data/raw/qd-20-2022-archive-candidate.pdf');path.write_bytes(r.content);pdf=PdfReader(path);texts=[p.extract_text() for p in pdf.pages];path.with_suffix('.native.txt').write_text('\f'.join(texts));row.update(path=str(path),sha256=digest(r.content),pages=len(pdf.pages),chars=sum(map(len,texts)))
  print(json.dumps(row))
asyncio.run(main())
