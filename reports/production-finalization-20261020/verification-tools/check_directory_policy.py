import json,uuid
from pathlib import Path
from datetime import timedelta
from dotenv import dotenv_values
from pydantic import SecretStr
from psycopg.conninfo import make_conninfo
from landlaw.config import Settings
from landlaw.models import Document,Claim,Evidence
from landlaw.ops import record_source_review
from landlaw.store import Store
from landlaw.citizen import source_policy_issues
from landlaw.security import utcnow,local_date,new_token

def main():
 root=Path('reports/production-finalization-20261020');name=json.loads((root/'directory-candidate-restore/isolated-databases.jsonl').read_text().splitlines()[-1])['database'];assert name.startswith('landlaw_restore_')
 v=dotenv_values('.env');s=Settings();owner=Store(s.model_copy(update={'database_url':SecretStr(make_conninfo(v['ADMIN_DATABASE_URL'],dbname=name)),'admin_database_url':SecretStr('')}));runtime=Store(s.model_copy(update={'database_url':SecretStr(make_conninfo(v['DATABASE_URL'],dbname=name)),'admin_database_url':SecretStr('')}))
 try:
  release=runtime.release(None,True);assert release['id']=='corpus-a09539ac704c6591'
  doc=Document.model_validate_json(Path('data/staging/citizen-directory-candidate-20261020/parsed-document.json').read_text());claim=Claim(kind='contact',text='Trụ sở Tiếp công dân Thành phố Hà Nội tại số349 phố Huế, phường Hai Bà Trưng, Hà Nội.',citation_ids=[doc.chunks[0].id])
  assert source_policy_issues(claim,[Evidence(document=doc,chunk=doc.chunks[0])],local_date())
  review=json.loads((root/'city-directory-source-review.json').read_text());receipt={'document_id':doc.id,'checksum':doc.checksum,'checked_at':utcnow().isoformat(),'status':'unchanged','relation_review':'Entire one-page institutional-address notice read; official publication metadata and later official Hanoi report corroborate349 Phố Huế. Address-only directory role, no deciding/receiving competence, phone, hours or filing procedure inferred. No legal rule is asserted from this directory; no procedural dependency needed for the address itself. AI technical review, not independent legal certification.','evidence_urls':[x['url'] for x in review['fetches']],'operational_review':{'source_role_checked':True,'jurisdiction_checked':True,'procedure_and_dependencies_checked':True}}
  path=root/'city-directory-operational-receipt.json';assert not path.exists();path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');record_source_review(owner,path)
  checked=runtime.operational_review(doc,release['id']);evidence=[Evidence(document=checked,chunk=doc.chunks[0])]
  assert not source_policy_issues(claim,evidence,local_date())
  assert source_policy_issues(claim.model_copy(update={'text':'Nộp khiếu nại Vành đai4 tại trụ sở này.'}),evidence,local_date())
  assert source_policy_issues(claim,evidence,local_date()-timedelta(days=1))
  sid=str(uuid.uuid4());token=new_token();runtime.create_session(sid,token);assert runtime.authenticate(sid,token)
  for table in ['messages','traces','answer_cache']:
   assert not runtime.rows("SELECT has_table_privilege(current_user,%s,'SELECT') AS r,has_table_privilege(current_user,%s,'INSERT') AS w",('public.'+table,'public.'+table))[0]['r']
   assert not runtime.rows("SELECT has_table_privilege(current_user,%s,'INSERT') AS w",('public.'+table,))[0]['w']
  result={'checked_at':utcnow().isoformat(),'passed':True,'candidate_corpus':release['id'],'isolated_database':name,'runtime_role_tested':True,'session_authentication':True,'history_read_and_write_privileges_revoked':True,'unreviewed_contact_blocked':True,'reviewed_public_address_allowed':True,'unsupported_filing_competence_blocked':True,'historical_directory_claim_blocked':True,'generation_calls':0,'serving_database_changed':False,'publication_approved':False,'scope':'Actual staged source, current operational receipt and PostgreSQL runtime role; deterministic source-policy verification only, not model evaluation or legal certification.'}
  (root/'city-directory-runtime-policy.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
 finally:runtime.close();owner.close()
try:main()
except Exception as e:print(json.dumps({'passed':False,'error_type':type(e).__name__}));raise SystemExit(1) from None
