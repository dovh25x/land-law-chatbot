import asyncio,json
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from landlaw.ingest import download
from landlaw.security import digest
from pypdf import PdfReader
async def main():
 url='https://vanban.hanoi.gov.vn/?pageid=27218&p_steering=188741'
 row={'url':url,'attachments':[]}
 async with httpx.AsyncClient(timeout=45,follow_redirects=True) as c:
  data,final=await download(c,url);Path('data/raw/qd-20-2023-user-publication.html').write_bytes(data)
  soup=BeautifulSoup(data,'html.parser')
  links=[urljoin(final,a['href']) for a in soup.select('a[href]') if '.pdf' in a['href'].lower() and any(t in a['href'].lower() for t in ['20-2023','20_2023','20.2023'])]
  row['publication_sha256']=digest(data)
  for i,link in enumerate(dict.fromkeys(links)):
   body,_=await download(c,link,url)
   if not body.startswith(b'%PDF'):continue
   path=Path(f'data/raw/qd-20-2023-user-official-{i+1}.pdf');path.write_bytes(body)
   reader=PdfReader(path);text='\f'.join(p.extract_text() for p in reader.pages)
   path.with_suffix('.native.txt').write_text(text)
   row['attachments'].append({'url':link,'path':str(path),'sha256':digest(body),'pages':len(reader.pages),'chars':len(text)})
 print(json.dumps(row,ensure_ascii=False))
 Path('reports/corpus-remediation-20261018/qd20-user-official.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
asyncio.run(main())
