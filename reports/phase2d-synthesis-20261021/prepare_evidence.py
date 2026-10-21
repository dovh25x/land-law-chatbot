"""Bind the completed offline evidence to code/corpus/suite identities. No DB/API."""
import hashlib,json,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
b=Path('reports/phase2d-synthesis-20261021')
old=json.loads(Path('reports/phase2c-current-20261021/release-manifest-reviewed.json').read_text())
accept=json.loads((b/'acceptance-locked/report.json').read_text())
hist=json.loads((b/'historical-locked/report.json').read_text())
baseline=json.loads((b/'baseline.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
changed=[p for p,h in baseline['sha256'].items() if not Path(p).is_file() or sha(p)!=h]
assert sorted(changed)==['backend/landlaw/agent.py','backend/landlaw/evaluation.py','tests/conftest.py','tests/test_agent.py','tests/test_citizen.py','tests/test_quality_candidate.py','tests/test_s06_clause_context.py','tests/test_source_review_policy.py'],changed
corpus='data/staging/phase2c-current/release-v5.json'
assert sha(corpus)==old['candidate_identity_components']['corpus_payload']
suites={p:sha(p) for p in old['candidate_identity_components']['evaluation_suites']}
assert suites==old['candidate_identity_components']['evaluation_suites']
assert '486 passed' in (b/'backend-locked.log').read_text()
assert accept['all_three_complete'] and accept['inputs_unchanged'] and accept['runtime_unchanged']
settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',groq_api_key='',allow_stale_generation=False)
assert configuration_fingerprint(settings)==accept['runtime_fingerprint']
paths=subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z']).decode().split('\0')
source={p:sha(p) for p in sorted(set(paths)) if p and not p.startswith('reports/') and Path(p).is_file()}
tree=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
(b/'source-files-sha256.json').write_text(json.dumps(source,indent=2)+'\n')
stages=[]
for row in accept['cases']:
    diag=row['diagnostics'];full=row['retrieval']
    aliases={cid:shown['citation_id'] for cid,shown in zip(row['synthesis_sources'],(row.get('synthesis_payload') or {}).get('evidence',[]))}
    excluded={cid:reason for cid,reason in full.items() if reason!='retained'}
    excluded.update({cid:reason for cid,reason in diag.get('selection_reasons',{}).items() if not reason.startswith('included')})
    stages.append({'id':row['id'],'retrieved_sources':list(full),'retained_sources':[c['citation_id'] for c in row['retained_context']],
        'admission_evaluated_on':'retained sources only; sources outside evidence cap were not sent for synthesis',
        'admitted_sources':diag.get('admitted_sources',[]),
        'synthesis_sources':[{'id':cid,'alias':aliases.get(cid),'document_id':s['document_id'],'locator':s['locator'],
            'provided_text_sha256':hashlib.sha256(s['text'].encode()).hexdigest()} for cid,s in row['synthesis_sources'].items()],
        'verified_citations':diag.get('verified_citations',[]),'released_citations':row['output_citations'],
        'missing_required_sources':[x for x in row['source_requirements'] if not x['present']],
        'missing_legal_dependencies':diag.get('missing_legal_dependencies',[]),'exclusion_reasons':excluded})
(b/'evidence-stages.json').write_text(json.dumps({'input_report_sha256':sha(b/'acceptance-locked/report.json'),
    'scope':'Derived from captured real pipeline state. Empty verified citations on intentional capture abstentions are not model failures.',
    'cases':stages},ensure_ascii=False,indent=2)+'\n')
expected={'S01':'answered','S02':'clarification_needed','S03':'answered','N07':'clarification_needed','N08':'insufficient_evidence'}
assert all(r['output_status']==expected[r['id']] for r in hist['cases'])
(b/'historical-summary.json').write_text(json.dumps({'input_report_sha256':sha(b/'historical-locked/report.json'),
    'scope':'Existing deterministic source rules/clarification/refusal only; no answer fixture.',
    'passed':True,'model_pass':None,'cases':[{'id':r['id'],'expected':expected[r['id']],
      'actual':r['output_status'],'origin':r['synthesis_origin']} for r in hist['cases']]},ensure_ascii=False,indent=2)+'\n')
protection={'checked_at':datetime.now(timezone.utc).isoformat(),'baseline_files':len(baseline['sha256']),
    'unchanged_existing_files':len(baseline['sha256'])-len(changed),'changed_existing_files':changed,
    'head_unchanged':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==baseline['head'],
    'corpus_payload_unchanged':True,'frozen_suites_unchanged':True,
    'prior_reports_unchanged':all(not p.startswith('reports/') for p in changed)}
(b/'protection.json').write_text(json.dumps(protection,indent=2)+'\n')
components={'source_tree':tree,'runtime_sqlite':accept['runtime_fingerprint'],
    'runtime_pg_planned':configuration_fingerprint(settings.model_copy(update={'database_url':SecretStr('postgresql://not-used/candidate')})),
    'corpus_payload':sha(corpus),'source_policy':old['candidate_identity_components']['source_policy'],'evaluation_suites':suites}
identity=hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest()
manifest={'format':1,'phase':'2D','prepared_at':datetime.now(timezone.utc).isoformat(),
    'timebox_started_at':'2026-10-21T05:29:13+00:00','timezone':'Asia/Ho_Chi_Minh',
    'phase_2d_status':'PASS_DETERMINISTIC_CONTEXT_AND_CITATION_INTEGRITY',
    'full_pipeline_answer_acceptance_established':False,'synthesis_input_integrity_established':True,
    'model_pilot_decision':'READY_PENDING_EXPLICIT_APPROVAL','deployment_decision':'NOT_READY',
    'git':{'base_commit':baseline['head'],'candidate_commit':None,'working_tree_dirty':True,'source_tree_sha256':tree},
    'candidate_identity_components':components,'candidate_identity_sha256':identity,
    'runtime':{'sqlite_fingerprint_verified':accept['runtime_fingerprint'],'postgresql_fingerprint_planned_only':components['runtime_pg_planned'],
        'python_tested':sys.version.split()[0],'model':old['runtime']['model'],'embedding_contract':old['runtime']['embedding_contract']},
    'corpus':{'id':accept['corpus_id'],'path':corpus,'payload_sha256':sha(corpus),'modified_in_phase2d':False},
    'source_policy':{'path':'reports/phase2c-current-20261021/source-gate-final.json',
        'canonical_sha256':components['source_policy'],'scope_date':'2026-10-21','receipts_modified':False},
    'evaluation_suites':suites,'context_budget':{'serialized_evidence_and_document_chars':7000,
        'serialization':'Actual Groq compact JSON with C aliases, including clause/scope metadata',
        'llm_requests_per_turn_including_retries':6,'tools':12,'retrieval_rounds':2,'repairs':1,'turn_seconds':90},
    'checks':{'backend':{'passed':486,'log':str(b/'backend-locked.log')},
        'new_regressions':{'passed':25,'log':str(b/'backend-locked.log')},
        'actual_synthesis_source_completeness':{'passed':3,'total':3,'model_pass':None,
            'wire_context_chars':{r['id']:r['wire_context_chars'] for r in accept['cases'][:3]}},
        'historical_deterministic_controls':{'passed':5,'total':5},'secrets_scan':'PASS','git_diff_check':'PASS',
        'frontend':'NOT_RERUN_UNCHANGED','postgresql':'NOT_TESTED_NO_LOCAL_SERVER','public_e2e':'NOT_TESTED',
        'groq_requests':0,'judge_requests':0},
    'model_quality':{'answer_correctness':None,'faithfulness':None,'citation_accuracy_semantic':None,'model_latency':None,
        'answerable_coverage':None,'false_abstention_rate':None,'S06':'FAIL_PREVIOUS_ATTEMPT_UNCHANGED'},
    'deployment_blockers':['Model pilot/semantic review not run','PostgreSQL candidate not verified',
        'Deployed SHA/corpus/policy/fingerprint not matched to this uncommitted candidate',
        'Public ingress/SSE/citation E2E not verified','Current source scopes limited to 2026-10-21'],
    'commit_performed':False,'push_performed':False,'deployment_performed':False,'production_database_modified':False}
(b/'release-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'phase2d':manifest['phase_2d_status'],'identity':identity,
    'source_tree':tree,'runtime_sqlite':accept['runtime_fingerprint'],'protected_existing_files':protection['unchanged_existing_files']}))
