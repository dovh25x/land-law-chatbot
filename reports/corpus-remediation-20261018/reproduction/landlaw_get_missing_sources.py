import asyncio,json
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from landlaw.ingest import download
from landlaw.security import digest
async def main():
 sources=[('qd-10-2017-hanoi','https://vanban.chinhphu.vn/?pageid=27160&docid=189167'),('nd-01-2017','https://vanban.chinhphu.vn/?pageid=27160&docid=187962'),('nd-148-2020','https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-148-2020-nd-cp-32748.htm')]
 rows=[]
 async with httpx.AsyncClient(timeout=40) as client:
  for ident,url in sources:
   row={'id':ident,'url':url,'attachments':[]}
   try:
    data,final=await download(client,url)
    page=Path('data/raw')/(ident+'-new-official-publication.html');page.write_bytes(data)
    soup=BeautifulSoup(data,'html.parser')
    links=list(dict.fromkeys(urljoin(final,a['href']) for a in soup.select('a[href]') if '.pdf' in a['href'].lower()))[:3]
    for i,link in enumerate(links):
     content,attachment_final=await download(client,link,url)
     if not content.startswith(b'%PDF'):continue
     path=Path('data/raw')/(ident+f'-new-official-{i+1}.pdf');path.write_bytes(content)
     row['attachments'].append({'url':link,'path':str(path),'sha256':digest(content)})
   except Exception as exc:row['error_type']=type(exc).__name__
   rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 Path('reports/corpus-remediation-20261018/missing-source-fetch.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
asyncio.run(main())
