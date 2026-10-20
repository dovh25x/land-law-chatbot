import asyncio,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import httpx
from landlaw.ingest import collect_source
from landlaw.config import Settings
async def main():
 sources={s['id']:s for s in json.loads(Path('data/sources.json').read_text())};rows=[]
 async with httpx.AsyncClient(timeout=30,follow_redirects=True) as c:
  for key in ['nq-254-2025','qd-56-2024-hanoi']:
   s=sources[key];row={'document_id':key,'url':s['url'],'approved_freshness':False}
   try:
    r=await c.get(s['url']);row.update(status=r.status_code,resolved_url=str(r.url));r.raise_for_status();p=Path('data/raw/citizen-finalization-20261020')/(key+'-followup.html');p.write_bytes(r.content);sha=hashlib.sha256(r.content).hexdigest();proposal={**s,'raw_paths':[str(p)],'raw_checksums':{str(p):sha}};row.update(raw_path=str(p),sha256=sha)
    doc=await collect_source(proposal,Settings(),c,offline=True,allow_ocr=False);row['parsed_chunks']=len(doc.chunks)
   except Exception as e:row.update(error_type=type(e).__name__,diagnostic=str(e)[:240] if type(e).__name__=='Quarantine' else None)
   rows.append(row)
 Path('reports/production-finalization-20261020/active-source-followup.json').write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Technical download/parser diagnosis only, no freshness approval or serving mutation','results':rows},ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows,ensure_ascii=False))
asyncio.run(main())
