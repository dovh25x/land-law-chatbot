import asyncio,json
from pathlib import Path
import httpx
from landlaw.security import digest,utcnow

async def main():
 root=Path('reports/corpus-audit-20261018-e1db9ef')
 sources=json.loads(Path('data/sources.json').read_text())
 docs=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())['documents']
 selected=['luat-dat-dai-2024','nd-226-2025','qd-40-2026-hanoi','ring4-nq56-2022','luat-thu-do-2026']
 rows=[]
 async with httpx.AsyncClient(timeout=25,follow_redirects=True,headers={'User-Agent':'HanoiLandLawResearch/0.1 corpus-audit'}) as client:
  async def check(ident):
   doc=next(d for d in docs if d['id']==ident)
   if not doc['source_files']:return
   attachment=doc['source_files'][0]
   row={'id':ident,'url':attachment['url'],'expected_sha256':attachment['checksum']}
   try:
    res=await client.get(attachment['url'])
    row.update({'http_status':res.status_code,'pdf':res.content.startswith(b'%PDF'),'bytes':len(res.content),'download_sha256':digest(res.content)})
    row['matches_snapshot_bytes']=res.status_code==200 and row['pdf'] and row['download_sha256']==row['expected_sha256']
   except Exception as exc:row['error_type']=type(exc).__name__
   rows.append(row)
  await asyncio.gather(*(check(ident) for ident in selected))
  live={}
  for path in ['/readyz','/api/v1/status']:
   try:
    response=await client.get('https://hanoi-land-law.pages.dev'+path)
    live[path]={'status':response.status_code,'body':response.json()}
   except Exception as exc:live[path]={'error_type':type(exc).__name__}
 root.joinpath('live-source-samples.json').write_text(json.dumps({'checked_at':utcnow().isoformat(),'scope':'Five first PDF attachments, byte comparison only; does not review later amendments or refresh source receipts.','results':rows},ensure_ascii=False,indent=2)+'\n')
 root.joinpath('live-status.json').write_text(json.dumps({'checked_at':utcnow().isoformat(),'results':live},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'samples':[{k:v for k,v in r.items() if k not in ['url','download_sha256','expected_sha256']} for r in rows],'live':live},ensure_ascii=False))
asyncio.run(main())
