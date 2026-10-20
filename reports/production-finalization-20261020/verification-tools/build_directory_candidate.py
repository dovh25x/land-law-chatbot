import asyncio,copy,hashlib,json,tempfile
from pathlib import Path
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.models import Document
from landlaw.provider import GroqProvider
from landlaw.store import Store
from landlaw.publication import validate_corpus
from landlaw.security import digest,utcnow
from landlaw.ingest import coverage
async def main():
 stage=Path('data/staging/citizen-directory-candidate-20261020');source=Path('data/staging/production-backup-check-20261020/release.json');old=json.loads(source.read_text());doc=Document.model_validate_json((stage/'parsed-document.json').read_text());assert doc.id not in {d['id'] for d in old['documents']}
 with tempfile.TemporaryDirectory(prefix='landlaw-directory-candidate-') as temp:
  s=Settings().model_copy(update={'database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(temp)/'candidate.db')});store=Store(s);provider=GroqProvider(s,store)
  try:
   vectors=await provider.embed_many([c.text for c in doc.chunks],title=doc.title)
   for chunk,vector in zip(doc.chunks,vectors,strict=True):chunk.embedding=vector;chunk.embedding_model=s.embedding_model
   payload=copy.deepcopy(old);payload['documents'].append({**doc.model_dump(mode='json'),'chunks':[{**c.model_dump(mode='json'),'embedding':c.embedding} for c in doc.chunks]})
   identity={key:payload[key] for key in ['documents','relations','unresolved_relations','coverage_gaps','embedding_contract','place_aliases','embedding_model']};identity['parser_version']=15
   payload['id']='corpus-'+digest(json.dumps(identity,sort_keys=True,ensure_ascii=False))[:16]
   assert payload['documents'][:-1]==old['documents'];validate_corpus(payload)
   (stage/'candidate.json').write_text(json.dumps(payload,ensure_ascii=False))
   store.stage(payload);store.publish(payload['id']);store.backup(stage/'candidate-backup.json')
   result={'checked_at':utcnow().isoformat(),'source_corpus_id':old['id'],'candidate_corpus_id':payload['id'],'source_snapshot_sha256':digest(source.read_bytes()),'candidate_sha256':digest((stage/'candidate.json').read_bytes()),'backup_sha256':digest((stage/'candidate-backup.json').read_bytes()),'documents':len(payload['documents']),'preserved_existing_documents_exactly':len(old['documents']),'preserved_existing_vectors_exactly':sum(len(d['chunks']) for d in old['documents']),'new_vectors_generated':len(vectors),'embedding_attempts_including_failed_packaging':2,'embedding_contract':payload['embedding_contract'],'generation_calls':0,'active_manifest_changed':False,'serving_database_changed':False,'publication_approved':False,'coverage':coverage(payload),'operational_activation_receipt_still_required':True,'scope':'Additive offline candidate only. One fully reviewed public-address source; existing corpus bytes/vectors retained. No legal/quality acceptance or production activation.'}
   Path('reports/production-finalization-20261020/city-directory-candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['candidate_corpus_id','documents','preserved_existing_vectors_exactly','new_vectors_generated','generation_calls']}))
  finally:await provider.close();store.close()
asyncio.run(main())
