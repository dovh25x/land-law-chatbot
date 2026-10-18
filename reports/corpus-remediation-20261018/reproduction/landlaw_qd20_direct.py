import asyncio,json
from pathlib import Path
import httpx
from landlaw.security import digest
async def main():
 urls=[
 'https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/164473/VanBanGoc_QDPQ-20-2023.pdf',
 'https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/164473/VanBanGoc_20.2023.pdf',
 'https://storage-vnportal.vnpt.vn/gov-hni/CrawlDownloads/vanban-hanoi-gov-vn/documents/10182/2518750/QDPQ-20-2023.pdf',
 'https://storage-vnportal.vnpt.vn/gov-hni/CrawlDownloads/vanban.hanoi.gov.vn/documents/10182/2518750/QDPQ-20-2023.pdf']
 async with httpx.AsyncClient(timeout=25,follow_redirects=True) as c:
  async def get(i,u):
   try:
    r=await c.get(u);row={'url':u,'status':r.status_code,'pdf':r.content.startswith(b'%PDF')}
    if row['pdf']:
     p=Path(f'data/raw/qd20-direct-candidate-{i}.pdf');p.write_bytes(r.content);row.update(path=str(p),sha256=digest(r.content))
    return row
   except Exception as e:return {'url':u,'error_type':type(e).__name__}
  rows=await asyncio.gather(*(get(i,u) for i,u in enumerate(urls)))
  print(json.dumps(rows,ensure_ascii=False))
asyncio.run(main())
