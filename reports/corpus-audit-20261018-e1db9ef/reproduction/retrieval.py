import asyncio,json,tempfile,math
from pathlib import Path
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.provider import GroqProvider
from landlaw.evaluation import evaluate_retrieval
from landlaw.security import digest,utcnow

ROOT=Path('reports/corpus-audit-20261018-e1db9ef')
async def main():
 base=Settings()
 snapshot=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())
 with tempfile.TemporaryDirectory(prefix='landlaw-corpus-audit-') as folder:
  settings=base.model_copy(update={'app_env':'development','database_url':SecretStr(''),'admin_database_url':SecretStr(''),
   'sqlite_path':str(Path(folder)/'evaluation.db'),'reports_dir':ROOT/'sqlite'})
  local=Store(settings)
  try:
   local.restore(Path('data/backups/ring4-public-corpus.json'))
   restored=local.release()
   expected={c['id']:c['checksum'] for d in snapshot['documents'] for c in d['chunks']}
   actual={c['id']:c['checksum'] for d in restored['documents'] for c in d['chunks']}
   assert restored['id']==snapshot['id'] and expected==actual
   (ROOT/'restore.json').write_text(json.dumps({'passed':True,'database':'isolated temporary SQLite','corpus_id':restored['id'],
    'documents':len(restored['documents']),'chunks':len(actual),'all_chunk_checksums_match_snapshot':True,
    'backup_sha256':digest(Path('data/backups/ring4-public-corpus.json').read_bytes()),'contains_server_history':False},indent=2)+'\n')
   for label,store,selected in [('sqlite',local,settings),('postgresql',None,base.model_copy(update={'reports_dir':ROOT/'postgresql'}))]:
    if store is None:store=Store(selected)
    provider=GroqProvider(selected,store)
    try:
     metadata=store.release(None,True)
     assert metadata['id']==snapshot['id']
     assert {d['id']:d['checksum'] for d in metadata['documents']}=={d['id']:d['checksum'] for d in snapshot['documents']}
     for split in ('smoke','supplemental','natural'):
      report=await evaluate_retrieval(selected,store,provider,split)
      print(json.dumps({'backend':label,'split':split,'eligible':report['eligible_cases'],'recall_at_8':report['gold_recall_at_8'],'hits':report['hits']}),flush=True)
     if label=='sqlite':
      samples=[]
      for ident in ('luat-dat-dai-2024','nd-88-2024','qd-40-2026-hanoi','nd-226-2025','ring4-nq56-2022','nq-254-2025'):
       doc=next(d for d in snapshot['documents'] if d['id']==ident)
       chunk=next(c for c in doc['chunks'] if not c['id'].endswith('parent') and len(c['text'])>200)
       vector=(await asyncio.to_thread(provider.local_embeddings.embed_many,[chunk['text']],doc['title'],False))[0]
       old=chunk['embedding']; cosine=sum(a*b for a,b in zip(vector,old))/math.sqrt(sum(v*v for v in vector)*sum(v*v for v in old))
       samples.append({'document_id':ident,'chunk_id':chunk['id'],'cosine_with_snapshot':cosine,'matches_within_1e-5':cosine>1-1e-5})
      (ROOT/'embedding-samples.json').write_text(json.dumps({'checked_at':utcnow().isoformat(),'contract':snapshot['embedding_contract'],
       'scope':'Recompute six samples for validation only; corpus embeddings unchanged, not a full vector audit.','samples':samples},ensure_ascii=False,indent=2)+'\n')
    finally:
     await provider.close()
     if label!='sqlite':store.close()
  finally:local.close()
asyncio.run(main())
