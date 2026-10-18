import asyncio,json
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from landlaw.security import digest
async def main():
 urls=['https://vanban.hanoi.gov.vn/?p_steering=210964&pageid=27218','https://luatgpt.vn/van-ban-ubnd/20-2023-qd-ubnd-quyet-dinh-so-20-2023-qd-ubnd-ve-viec-sua-doi-bo-sung-dieu-chinh-quyet-dinh-so-30-2019-qd-ubnd-ngay-31-12-2019-cua-ubnd-thanh-pho-ha-noi-ve-viec-ban-hanh-quy-dinh-v']
 async with httpx.AsyncClient(timeout=25,follow_redirects=True) as c:
  for i,url in enumerate(urls):
   try:
    r=await c.get(url);p=Path(f'data/raw/portal-retry-{i}.html');p.write_bytes(r.content)
    links=[urljoin(str(r.url),a['href']) for a in BeautifulSoup(r.content,'html.parser').select('a[href]') if any(t in a['href'].lower() for t in ['pdf','20-2023','20_2023'])]
    print(json.dumps({'url':url,'status':r.status_code,'sha256':digest(r.content),'links':links},ensure_ascii=False),flush=True)
   except Exception as e:print(json.dumps({'url':url,'error_type':type(e).__name__}),flush=True)
asyncio.run(main())
