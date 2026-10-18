import asyncio,json
from pathlib import Path
import httpx
from landlaw.ingest import download,html_text
from landlaw.security import digest,utcnow

ROOT=Path('reports/corpus-remediation-20261018')
async def main():
 sources=json.loads(Path('data/sources.json').read_text())
 release=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())
 docs={d['id']:d for d in release['documents']}
 sem=asyncio.Semaphore(4)
 rows=[]
 async with httpx.AsyncClient(timeout=35,headers={'User-Agent':'HanoiLandLawResearch/0.1 source-review'}) as client:
  async def fetch(source):
   async with sem:
    ident=source['id'];row={'id':ident,'checked_at':utcnow().isoformat(),'attachments':[]}
    doc=docs.get(ident)
    urls=source.get('attachment_urls',[]) or [s['url'] for s in (doc or {}).get('source_files',[])]
    for index,url in enumerate(urls):
     entry={'url':url}
     try:
      data,final=await download(client,url,source.get('publication_url') or source['url'])
      path=Path('data/raw')/(ident+f'-remediation-live-{index+1}.pdf')
      path.write_bytes(data)
      old={a['checksum'] for a in (doc or {}).get('source_files',[])}|set(source.get('raw_checksums',{}).values())
      entry.update({'path':str(path),'sha256':digest(data),'pdf':data.startswith(b'%PDF'),'matches_reviewed_artifact':digest(data) in old})
     except Exception as exc:entry['error_type']=type(exc).__name__
     row['attachments'].append(entry)
    try:
     data,final=await download(client,source['url'],source.get('publication_url'))
     path=Path('data/raw')/(ident+'-remediation-publication.html');path.write_bytes(data)
     row['publication']={'path':str(path),'url':final,'sha256':digest(data)}
     try:
      content=html_text(data,legal=source['source_kind']=='legal')
      row['publication']['substantive_text_sha256']=digest(content[0][1])
      row['publication']['characters']=len(content[0][1])
     except Exception:pass
    except Exception as exc:row['publication']={'error_type':type(exc).__name__}
    rows.append(row)
    (ROOT/'source-fetch-progress.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'source_fetch':ident,'attachments':len(row['attachments']),'publication_ok':'path' in row['publication']}),flush=True)
  await asyncio.gather(*(fetch(s) for s in sources))
 (ROOT/'source-fetch.json').write_text(json.dumps({'started_scope':'All 64 manifest sources; byte checks alone are not legal or relation review.','results':rows},ensure_ascii=False,indent=2)+'\n')
asyncio.run(main())
