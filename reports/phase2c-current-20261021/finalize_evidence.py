"""Finalize local, explicitly NOT_READY evidence; never publishes or touches a DB."""
import hashlib,json,subprocess,zipfile
from collections import Counter
from datetime import datetime,timezone,date
from pathlib import Path
base=Path('reports/phase2c-current-20261021');asset=Path('dist/phase2c-current-20261021')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
now=datetime.now(timezone.utc).isoformat();allowed={'backend/landlaw/agent.py','backend/landlaw/store.py','data/legal_relations.json'}
baseline=read(base/'baseline-checksums.json');changes=[p for p,h in baseline.items() if not Path(p).is_file() or sha(p)!=h]
assert set(changes)==allowed,changes
old_package=read('reports/phase2b-rc-20261021/release-manifest.json')['git']['package_source_files_sha256']
old_changed=[p for p,h in old_package.items() if not Path(p).is_file() or sha(p)!=h]
assert set(old_changed)==allowed,old_changed
old=read('data/staging/production-backup-check-20261020/release.json');candidate=read('data/staging/phase2c-current/release-v5.json')
assert len(old['documents'])==len(candidate['documents'])==60
for before,after in zip(old['documents'],candidate['documents'],strict=True):
 assert {k:v for k,v in before.items() if k!='chunks'}=={k:v for k,v in after.items() if k!='chunks'}
 assert before['chunks']==after['chunks'][:len(before['chunks'])]
assert sum(len(d['chunks']) for d in candidate['documents'])-sum(len(d['chunks']) for d in old['documents'])==4
proof=read(base/'provision-provenance-v5.json');replay=read(base/'acceptance-date-fix/report.json');startup=read(base/'scope-and-startup.json');pack=read(asset/'manifest.json');pilot=read(base/'pilot-retrieval-final.json')
assert replay['inputs_unchanged'] and replay['runtime_unchanged']
assert replay['corpus_id']==candidate['id']==startup['corpus_id']==pack['corpus_id']
assert sha(asset/'corpus-backup.json')==replay['backup']['sha256']==pack['sha256']
assert all(replay['restore'].values())
assert replay['configuration_sha256']==startup['sqlite_configuration_sha256']
assert not startup['outbound_requests']
for name,count in [('backend-tests-date-fix.log',459),('backend-tests-py312-final.log',459),('current-tests-date-fix.log',22)]:assert f'{count} passed' in (base/name).read_text()
assert '100 passed' in (base/'frontend-e2e.log').read_text()
assert 'Tests  14 passed' in (base/'frontend-tests.log').read_text()
assert 'built in' in (base/'frontend-build.log').read_text()
assert 'No configured secret' in (base/'secrets-final.log').read_text()
# Existing source-tree identities must still equal the packaged candidate.
assert all(Path(p).is_file() and sha(p)==h for p,h in pack['source_files_sha256'].items())
protection={'checked_at':now,'baseline_files':len(baseline),'expected_modified_preexisting_files':sorted(changes),
 'all_other_preexisting_files_unchanged':True,'all_phase1_phase2b_artifacts_unchanged':True,
 'previous_untracked_code_and_tests_protected':True,'all_existing_document_metadata_chunks_and_vectors_unchanged':True,
 'raw_source_manifest_unchanged':sha('data/sources.json')==baseline['data/sources.json'],
 'frozen_suites_unchanged':all(sha(p)==h for p,h in baseline.items() if p.startswith('data/evaluation/')),
 'base_payload_sha256':sha('data/staging/production-backup-check-20261020/release.json'),
 'new_chunks':4,'new_relations':len(candidate['relations'])-len(old['relations']),
 'changed_relation_scope':'nd49 Article16(3g) -> partial repeal of nd226; no verifier relaxation',
 'model_files':{p:sha(p) for p in ['models/e5/model_quantized.onnx','models/e5/sentencepiece.bpe.model']}}
write(base/'protection.json',protection)
policy=read(base/'source-gate-final.json');policy_sha=hashlib.sha256(json.dumps(policy,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
assert policy_sha==startup['source_gate']['policy_sha256']
current=set();all_passages=set();receipts=[]
for p in sorted((base/'receipts-final').glob('*.json')):
 r=read(p);rid=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 if r['status']=='unchanged':assert policy['receipts'][r['document_id']]==rid
 for scope in r.get('verified_scope',[]):
  all_passages.update(scope['chunk_checksums'])
  if scope['as_of_from']<='2026-10-21'<scope['as_of_to']:current.update(scope['chunk_checksums'])
 receipts.append({'path':str(p),'file_sha256':sha(p),'receipt_sha256':rid,'document_id':r['document_id'],'status':r['status']})
# Bundle only final review material, never superseded proposal receipts.
contents={str(p.relative_to(base)):p for p in (base/'receipts-final').glob('*.json')}
for name in ['source-gate-final.json','LEGAL_REVIEW.md','provision-provenance-v5.json','acceptance-cases-final.json']:
 contents[name]=base/name
zip_path=asset/'source-reviews-final.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for name,p in sorted(contents.items()):
  info=zipfile.ZipInfo(name,date_time=(2026,10,21,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
with zipfile.ZipFile(zip_path) as z:assert all(z.read(n)==p.read_bytes() for n,p in contents.items())
write(base/'source-review-bundle.json',{'path':str(zip_path),'sha256':sha(zip_path),'roundtrip_exact':True,'files':{n:sha(p) for n,p in contents.items()},'policy_sha256':policy_sha,'contains_provisional_receipts':False})
def scenario_definition(v):return [{k:x for k,x in c.items() if k!='fixture_claims'} for c in v['cases']]
assert scenario_definition(read(base/'acceptance-cases.json'))==scenario_definition(read(base/'acceptance-cases-final.json'))
rows=[{'id':r['id'],'expected_status':r['expected_status'],'actual_status':r.get('answer',{}).get('status'),
 'status_matches':r['status_matches'],'required_articles_reviewed':r.get('all_required_articles_reviewed'),
 'citation_integrity':r.get('citation_integrity'),'citation_count':len(r.get('answer',{}).get('citations',[])),
 'elapsed_ms_local_fixture_only':r['elapsed_ms']} for r in replay['cases']]
summary={'checked_at':now,'current_source_admission_before':[r['all_required_citations_admitted'] for r in startup['before_source_admission']],
 'current_source_admission_after':[r['all_required_citations_admitted'] for r in startup['after_source_admission']],
 'source_admission_is_not_retrieval_or_model_pass':True,'current_fixture_acceptance':{'passed':2,'answerable_cases':3,'false_abstentions':1,'failed_ids':['C01']},
 'negative_controls_passed':3,'historical_controls_passed':6,'external_llm_requests':0,'model_pass':None,
 'unchanged_question_and_expected_answer_definitions':True,'cases':rows}
write(base/'acceptance-summary.json',summary)
manifest={'format':1,'phase':'2C','prepared_at':now,'timebox_started_at':'2026-10-20T18:03:03+00:00','timezone':'Asia/Ho_Chi_Minh','status':'NOT_READY',
 'git':{'base_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'candidate_commit_sha':None,'working_tree_dirty':True,'source_tree_sha256':pack['source_tree_sha256'],'package_manifest':str(asset/'manifest.json')},
 'runtime':{'sqlite_configuration_sha256_verified':startup['sqlite_configuration_sha256'],'postgresql_configuration_sha256_planned_only':startup['postgresql_configuration_sha256_planned_only'],
 'model':startup['model'],'embedding':startup['embedding'],'dimensions':384,'embedding_contract':candidate['embedding_contract'],'provider_changed':False},
 'corpus':{'id':candidate['id'],'base_id':old['id'],'documents':60,'chunks':7396,'new_source_bound_chunks':4,'existing_vectors_unchanged':True,
 'payload_path':'data/staging/phase2c-current/release-v5.json','payload_sha256':sha('data/staging/phase2c-current/release-v5.json'),
 'backup_path':str(asset/'corpus-backup.json'),'backup_sha256':sha(asset/'corpus-backup.json'),'backup_bytes':(asset/'corpus-backup.json').stat().st_size,'local_restore':replay['restore']},
 'source_policy':{'path':str(base/'source-gate-final.json'),'canonical_sha256':policy_sha,'reviewed_unique_passages_all_intervals':len(all_passages),'reviewed_current_passages_2026_10_21':len(current),
 'current_substantive_as_of_from':'2026-10-21','current_substantive_as_of_to_exclusive':'2026-10-22','whole_corpus_state_counts':dict(Counter(replay['whole_corpus_source_states'].values())),
 'whole_corpus_verified':False,'receipts':receipts,'bundle_path':str(zip_path),'bundle_sha256':sha(zip_path)},
 'evaluation':{'frozen_suites_sha256':{p:sha(p) for p in ['data/evaluation/smoke.jsonl','data/evaluation/supplemental.jsonl','data/evaluation/natural.jsonl']},
 'current_acceptance_cases_sha256':sha(base/'acceptance-cases-final.json'),'current_fixture_answerable_coverage':{'numerator':2,'denominator':3},'current_fixture_false_abstention_rate':{'numerator':1,'denominator':3},
 'model_evaluated':False,'external_llm_requests':0,'ragas_faithfulness':None,'model_faithfulness':None,'model_citation_accuracy':None,'model_answer_correctness':None,'model_latency':None,
 'fixed_pilot_retrieval':{'case_ids':[r['id'] for r in pilot['results']],'n':pilot['eligible_cases'],'recall_at_5':pilot['gold_recall_at_5'],'storage_backend':'isolated_sqlite','report':str(base/'pilot-retrieval-final.json')},
 's06_status':'Prior real-model FAIL retained unchanged; no new model attempt; not transplanted as a score for this candidate.'},
 'checks':{'backend_python_3_14_4':'459 passed','backend_python_3_12_15':'459 passed','new_current_regressions':'22 passed','frontend_tests':'14 passed','frontend_build':'passed','playwright_local_mocked':'100 passed','secrets_scan':'passed','git_diff_check':'passed',
 'sqlite_startup_http':[r['status'] for r in startup['startup']],'sqlite_restore_exact':True,'missing_receipts_fail_closed':True,'model_pilot_run':False,'postgresql_verified':False,'public_e2e_verified':False,'container_build_verified_this_phase':False},
 'migrations_sha256':{str(p):sha(p) for p in sorted(Path('migrations').glob('*.sql'))},
 'blocking_conditions':['C01 remains an answerable current-law false abstention: governing Article98 and NQ254 Article3 are not retained together in its bounded context.',
 'Mandatory target of three distinct current legal groups is not met end-to-end:2/3 fixture cases only.',
 'Real-model pilot, semantic citation/correctness/faithfulness and cloud latency not evaluated for this candidate.',
 'PostgreSQL migration/runtime-role/restore/retrieval/capacity and public signed-ingress E2E not verified.',
 'No candidate commit SHA, push or deployment; serving fingerprint not verified against candidate.',
 'Current substantive scope authorizes only as_of21Oct; later-day current operation requires a genuine new source review.'],
 'assets_published':False,'production_database_modified':False,'deployment_performed':False,'approval_required_before_commit_push_deploy_or_model':True}
identity={'source_tree':pack['source_tree_sha256'],'runtime_sqlite':startup['sqlite_configuration_sha256'],'runtime_pg_planned':startup['postgresql_configuration_sha256_planned_only'],
 'corpus_payload':manifest['corpus']['payload_sha256'],'source_policy':policy_sha,'evaluation_suites':manifest['evaluation']['frozen_suites_sha256']}
manifest['candidate_identity_components']=identity;manifest['candidate_identity_sha256']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
write(base/'release-manifest.json',manifest)
paths=Path('reports/phase2b-rc-20261021/reviewed-paths.txt').read_text().splitlines()+['data/legal_relations.json','scripts/prepare_current_legal_candidate.py','scripts/verify_current_legal_coverage.py','tests/test_current_legal_candidate.py','tests/fixtures/current-source-provisions.json',str(base)+'/']
(base/'reviewed-paths.txt').write_text('\n'.join(dict.fromkeys(paths))+'\n')
print(json.dumps({'status':manifest['status'],'candidate':candidate['id'],'identity':manifest['candidate_identity_sha256'],'scoped_passages':len(all_passages),'current_passages':len(current),'before_source_admission':summary['current_source_admission_before'],'after_source_admission':summary['current_source_admission_after'],'current_fixture_passed':2,'protected_files':len(baseline)-len(changes)},ensure_ascii=False))
