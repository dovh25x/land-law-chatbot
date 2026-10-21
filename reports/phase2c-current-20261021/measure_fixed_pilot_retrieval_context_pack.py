"""Read-only pilot retrieval diagnostic: four gold-bearing cases, zero LLM calls."""
import asyncio,hashlib,json,tempfile,time
from pathlib import Path
from datetime import date
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.local_embedding import Encoder,MODEL
from landlaw.ops import record_source_review,activate_source_gate
from landlaw.evaluation import configuration_fingerprint
from landlaw.security import utcnow

async def main():
 base=Path('reports/phase2c-current-20261021');plan_path=Path('reports/phase2b-rc-20261021/pilot-plan.json');plan=json.loads(plan_path.read_text())
 cases={r['id']:r for split in ('smoke','supplemental','natural') for line in (Path('data/evaluation')/(split+'.jsonl')).read_text().splitlines() if (r:=json.loads(line))}
 for name,expected in [('model_quantized.onnx',MODEL['onnx_sha256']),('sentencepiece.bpe.model',MODEL['tokenizer_sha256'])]:
  assert Encoder.file_sha(Path('models/e5')/name)==expected
 encoder=Encoder(Path('models/e5'))
 with tempfile.TemporaryDirectory(prefix='landlaw-pilot-retrieval-') as folder:
  settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',groq_api_key='',allow_stale_generation=False,sqlite_path=str(Path(folder)/'candidate.db'))
  store=Store(settings)
  try:
   store.restore(Path('data/staging/phase2c-current/acceptance-context-pack-backup.json'))
   for path in sorted((base/'receipts-final').glob('*.json')):record_source_review(store,path)
   activate_source_gate(store,base/'source-gate-final.json');release=store.release(None,True);rows=[]
   for ident in plan['case_ids']:
    c=cases[ident];gold=set(c.get('gold_chunk_ids',[]))
    if not gold:continue
    start=time.monotonic();vector=await asyncio.to_thread(encoder.encode,c['question'],True)
    hits=await asyncio.to_thread(store.search,c['question'],vector,c.get('project'),release['id'],settings.embedding_model,date.fromisoformat(c['as_of']))
    ids=[h.chunk.id for h in hits];top5=set(ids[:5]);passages=[(h.document.id,h.chunk.id,h.chunk.checksum) for h in hits[:5]]
    gate=store.scoped_source_reviews(release,passages,date.fromisoformat(c['as_of']))
    rows.append({'id':ident,'question':c['question'],'as_of':c['as_of'],'gold_chunk_ids':sorted(gold),'retrieved_chunk_ids':ids,'gold_recall_at_5':len(gold&top5)/len(gold),'gold_recall_at_8':len(gold&set(ids[:8]))/len(gold),'top5_source_gate':gate,'elapsed_ms':round((time.monotonic()-start)*1000)})
   report={'checked_at':utcnow().isoformat(),'pilot_plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'pilot_case_ids':plan['case_ids'],'eligible_cases':len(rows),'storage_backend':'isolated_sqlite','configuration_sha256':configuration_fingerprint(settings),'corpus_id':release['id'],'source_gate':store.source_gate_status(release),'gold_recall_at_5':sum(r['gold_recall_at_5'] for r in rows)/len(rows),'external_llm_requests':0,'results':rows,'scope':'Raw-question E5/hybrid top5 over four fixed pilot gold-bearing cases. No history rewrite or agent expansion. Diagnostic only, not full-suite or PostgreSQL/model evaluation; no claim of final pilot pass.'}
   (base/'pilot-retrieval-context-pack.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
   print(json.dumps({'eligible':len(rows),'Recall@5':report['gold_recall_at_5'],'per_case':[{k:r[k] for k in ('id','gold_recall_at_5')} for r in rows]}))
  finally:store.close()
asyncio.run(main())
