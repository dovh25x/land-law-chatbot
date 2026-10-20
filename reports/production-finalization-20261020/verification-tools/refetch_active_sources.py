import asyncio,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
import httpx
from landlaw.config import Settings
from landlaw.ingest import collect_source
from landlaw.security import official_url
async def main():
 root=Path('data/raw/citizen-finalization-20261020/active-refetch');root.mkdir(parents=True,exist_ok=False)
 snapshot=json.loads(Path('data/staging/production-backup-check-20261020/release.json').read_text());sources={s['id']:s for s in json.loads(Path('data/sources.json').read_text())};sem=asyncio.Semaphore(4);rows=[]
 async with httpx.AsyncClient(timeout=25,follow_redirects=True) as client:
  async def one(doc):
   async with sem:
    source=sources[doc['id']];row={'document_id':doc['id'],'scope':'Technical current-publication download/parser comparison only; no legal amendment/transition approval or freshness receipt.'}
    try:
     urls=source.get('attachment_urls') or [source['url']];files=[];fetches=[]
     for index,url in enumerate(urls):
      assert official_url(url,source.get('publication_url') or source['url'])
      r=await client.get(url);r.raise_for_status();assert official_url(str(r.url),source.get('publication_url') or source['url'])
      path=root/f"{doc['id']}-{index}{'.pdf' if r.content.startswith(b'%PDF') else '.html'}";path.write_bytes(r.content);sha=hashlib.sha256(r.content).hexdigest();files.append(str(path))
      fetches.append({'url':url,'resolved_url':str(r.url),'status':r.status_code,'path':str(path),'sha256':sha,'matches_reviewed_raw':sha in source.get('raw_checksums',{}).values()})
     proposal={**source,'raw_paths':files,'raw_checksums':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}}
     new=await collect_source(proposal,Settings(),client,offline=True,allow_ocr=False)
     before={c['id']:c['checksum'] for c in doc['chunks']};after={c.id:c.checksum for c in new.chunks}
     row.update(fetches=fetches,document_bytes_unchanged=new.checksum==doc['checksum'],chunks_identical=before==after,original_chunks=len(before),refetched_chunks=len(after),changed_chunk_ids=[k for k in before.keys()&after.keys() if before[k]!=after[k]],added_chunk_ids=sorted(after.keys()-before.keys()),removed_chunk_ids=sorted(before.keys()-after.keys()))
    except Exception as e:row.update(error_type=type(e).__name__)
    rows.append(row);print(json.dumps({'source_checked':doc['id'],'chunks_identical':row.get('chunks_identical'),'error_type':row.get('error_type')}),flush=True)
    output={'checked_at':datetime.now(timezone.utc).isoformat(),'corpus_id':snapshot['id'],'expected_documents':len(snapshot['documents']),'completed':len(rows),'active_corpus_changed':False,'source_receipts_created':False,'scope':'Downloads/parse equality are technical evidence; they do not prove absence of amendments. No model calls, embeddings or serving writes.','results':sorted(rows,key=lambda x:x['document_id'])}
    Path('reports/production-finalization-20261020/active-source-refetch.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
  await asyncio.gather(*(one(d) for d in snapshot['documents']))
asyncio.run(main())
