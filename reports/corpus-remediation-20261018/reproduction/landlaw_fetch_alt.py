import asyncio,json
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from landlaw.ingest import download
from landlaw.security import digest
async def main():
 rows=[]
 async with httpx.AsyncClient(timeout=45) as c:
  for ident,url in [('nd-148-2020','https://vanban.chinhphu.vn/?pageid=27160&docid=202022'),('qd-20-2023-hanoi','https://vbpl.vn/hanoi/Pages/ivbpq-toanvan.aspx?ItemID=164473&Keyword=')]:
   row={'id':ident,'url':url,'attachments':[]}
   try:
    data,final=await download(c,url)
    Path(f'data/raw/{ident}-alternate-publication.html').write_bytes(data)
    soup=BeautifulSoup(data,'html.parser')
    for a in soup.select('a[href]'):
     link=urljoin(final,a['href'])
     if '.pdf' not in link.lower():continue
     body,loc=await download(c,link,url)
     if not body.startswith(b'%PDF'):continue
     path=Path(f'data/raw/{ident}-alternate.pdf');path.write_bytes(body)
     row['attachments'].append({'url':link,'path':str(path),'sha256':digest(body)});break
   except Exception as exc:row['error_type']=type(exc).__name__
   rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 Path('reports/corpus-remediation-20261018/alternate-fetch.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
asyncio.run(main())
