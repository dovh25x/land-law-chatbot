"""Assemble a release receipt from actual independent evidence; no network/mutation."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).parent
CODE='ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec'
def read(name):return json.loads((ROOT/name).read_text())
ci=read('ci-final-release.json');assert ci['headSha']==CODE and ci['conclusion']=='success'
freeze=read('candidate-final-freeze.json');probe=read('image-probe-final.json')
pub=read('corpus-publication.json');db=read('post-publication-database.json')
front=read('cloudflare-deployment-final.json');assets=read('public-frontend-integrity-final.json')
ingress=read('ingress-final-deploy.json');backup=read('rollback-restore.json')
reports=sorted(ROOT.glob('qa/public-source-*/report.json'))
ui=json.loads(reports[-1].read_text())
assert ui['status'] in ('PASS_SOURCE_ONLY_PUBLIC_BROWSER','PARTIAL'),ui.get('error')
assert len(ui['browser_checks'])==2 and not ui['prohibited_requests'] and ui['model_requests']==0
assert {c['width'] for c in ui['browser_checks']}=={1440,390}
assert all(c['source_panel']=='PASS' and c['reload']=='PASS' and c['chat_disabled'] for c in ui['browser_checks'])
assert pub['status']==db['status']==assets['status']==probe['status']==backup['status']=='PASS'
assert front['current']['commit_hash']==CODE and ingress['signed_ingress_observed'] and ingress['unsigned_request_rejected']
assert pub['safe_runtime_fingerprint']==probe['postgresql_configuration_fingerprint']
assert db['pointers']['active_release']==pub['active_corpus']
# No application, dependency, corpus manifest or other non-report edits after the tested code commit.
assert not subprocess.check_output(['git','diff',CODE,'--name-only','--','.',':!reports'],text=True).strip()
extra=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
assert all(p.startswith('reports/') for p in extra)
manifest={'format':1,'created_at':datetime.now(UTC).isoformat(),
 'decision':'READY_FOR_RESTRICTED_SOURCE_LOOKUP','generative_chatbot_decision':'NOT_READY_DISABLED',
 'deployed_application_commit':CODE,'tested_source_tree_sha256':freeze['source_tree_sha256'],
 'publication_tag':'v0.1.0-academic-20261021','release_url':'https://github.com/dovh25x/land-law-chatbot/releases/tag/v0.1.0-academic-20261021',
 'git_identity_note':'Tag will include a documentation/evidence-only follow-up commit; deployed and CI-tested application bytes remain pinned to deployed_application_commit. Publication receipt records the actual tag target.',
 'ci':{'status':'PASS','source_sha':CODE,'url':ci['url'],'backend_python':'3.12','backend_tests':529,'frontend_unit_tests':16,'playwright_tests':110,'image':'PASS','npm_audit':'0 vulnerabilities at CI timestamp'},
 'local_validation':{'backend_python':'3.14.4','backend_tests':529,'postgresql_major':16,'source_lookup_api':'PASS','image_python':'3.12.15','image_id':read('serving-image-identity-final.json')['id'],'image_peak_rss_mib':read('docker-memory-ui-guard.log')['peak_rss_mib'],'memory_limit_mib':512},
 'deployment':{'frontend':'https://hanoi-land-law.pages.dev','backend':'https://land-law-chatbot.onrender.com','render_plan':'free','render_deployment_id':next(json.loads(line)['deploy_id'] for line in (ROOT/'render-deploy-final.jsonl').read_text().splitlines() if json.loads(line)['status']=='verified'),'cloudflare_deployment_id':front['current']['id'],'postgresql_version':db['postgres_version'],'database_bytes':db['database_bytes'],'credentials_changed':False,'schema_changed':False},
 'runtime':{'source_lookup_only':True,'generation_enabled':False,'allow_stale_generation':False,'postgresql_fingerprint':probe['postgresql_configuration_fingerprint'],'sqlite_fingerprint':probe['sqlite_fingerprint'],'model_provider':'groq','model':'openai/gpt-oss-120b','model_serving_use':'disabled','embedding_contract':freeze['runtime']['embedding_contract'],'budget_per_generative_turn':{'requests_including_retries':6,'tools':12,'retrieval_rounds':2,'repairs':1,'seconds':90}},
 'corpus':freeze['corpus']|{'backup_asset_sha256':read('release-preparation-publish.json')['sha256'],'documents':60,'chunks':7396,'whole_corpus_verified':False},
 'source_policy':freeze['source_policy'],'source_receipts_sha256':freeze['source_receipts_sha256'],'evaluation_suites':freeze['evaluation_suites'],
 'source_scope':{'2026-10-21':{'documents':7,'passages':43},'2024-08-02':{'passages':25},'2026-10-22_and_23':{'passages':1,'content':'QD40 header only; no current business-law coverage claim'},'whole_document_verified':False,'freshness_expiry':'No automatic date extension; new review required for unsupported dates.'},
 'public_validation':{'status':ui['status'],'evidence':str(reports[-1].relative_to(Path.cwd())),'signed_ingress':'PASS_NEGATIVE_PROBES','frontend_asset_integrity':'PASS','outside_scope_source_rejection':'PASS_EXISTING_ND71_404_AND_UNREVIEWED_DATE_EMPTY','generation':'UNAVAILABLE_DISABLED','follow_up':'UNAVAILABLE_DISABLED','human_turnstile':'NOT_TESTED','physical_mobile_device':'NOT_TESTED_EMULATED_ONLY','source_latency':'Raw GET timings recorded in public report; not model latency'},
 'evaluation':{'recall_at_5':{'macro':0.9736842105263158,'micro':0.9523809523809523,'queries':19,'gold_hits':20,'gold_chunks':21,'backend':'SQLite','runtime_fingerprint':'1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d','interpretation':'Historical retrieval-only cohort, not current answer accuracy or new serving-mode measurement'},'S06':'FAIL','Phase3A_C01':'INCOMPLETE','Phase3A_C02_C03':'NOT_RUN','new_independent_C02':'INCOMPLETE_ONE_REQUEST_HTTP400_JSON','new_C02_confirmed_usage':0,'new_C02_unknown_usage_upper_bound':19788,'new_C02_provider_usage_interpretation':'Usage absent: 0 confirmed is not proof of zero actual tokens/cost','current_semantic_citation_accuracy':'NOT_MEASURED','current_answer_correctness':'NOT_ESTABLISHED','ragas':'NOT_RUN','answerable_coverage_false_abstention_rate':'NOT_MEASURED'},
 'rollback':{'prior_corpus':pub['previous_release_retained'],'old_data_retained':True,'local_restore':'PASS_PG16','cloud_restore':'NOT_RUN','guide':'ROLLBACK_FINAL.md'},
 'limitations':['Academic verified-excerpt lookup; no generated legal conclusions or individual entitlements.','Source evidence reviewed for selected passages/dates only.','Normal human Turnstile and generative public chat/follow-up not verified.','Native PowerPoint rendering and physical-device test remain unverified.']}
(ROOT/'release-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
rows=[('Code/CI','ci-final-release.json'),('Frozen candidate','candidate-final-freeze.json'),('Final image','image-probe-final.json'),('Memory','docker-memory-ui-guard.log'),('Cloud deployment','render-deploy-final.jsonl'),('Frontend identity','cloudflare-deployment-final.json'),('Public JS/CSS','public-frontend-integrity-final.json'),('Public source/date rejection','public-source-rejections.json'),('Corpus activation','corpus-publication.json'),('Cloud PG role/metadata','post-publication-database.json'),('Backup restore','rollback-restore.json'),('Ingress rejection','ingress-final-deploy.json'),('Local source API PG','qa/source-lookup-pg-acceptance.json'),('Final committed source/gold preservation','qa/final-code-committed-verification.json'),('Latest public browser',str(reports[-1].relative_to(ROOT))),('First harness failure','qa/public-source-2026-10-21T10-26-18-876Z/report.json'),('Harness failure explanation','qa/public-source-run-01-harness-review.json'),('Independent C02 failure','pilot-C02/attempt.json'),('C02 review','qa/c02-pilot-review.md'),('Reload race and regression','qa/UI_UNKNOWN_RUNTIME_FIX.md'),('Public race diagnostic','qa/history-race-2026-10-21T10-37-55-451Z/report.json'),('Superseded CI failure','ci-ui-guard-superseded.json'),('Rollback procedure','ROLLBACK_FINAL.md')]
lines=['# Final release evidence index','',f'Deployed/tested application: `{CODE}`. Restricted source lookup only; generation disabled.','', '| Evidence | Path | SHA256 |','|---|---|---|']
for title,path in rows:
 p=ROOT/path;assert p.is_file()
 lines.append(f'| {title} | [{path}]({path}) | `{hashlib.sha256(p.read_bytes()).hexdigest()}` |')
lines+=['','Historical evidence and locked suites are preserved; see [Phase 4 index](../final-submission/2026-10-21/EVIDENCE_INDEX.md) and [academic evaluation](../submission-20261021/EVALUATION.md).','', 'The release manifest pins current serving identity. Retrieval metrics and failed model pilots retain their original runtime fingerprints. Local fixture tests do not stand in for public or model acceptance.']
(ROOT/'EVIDENCE_INDEX.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'decision':manifest['decision'],'public_status':ui['status'],'code_sha':CODE,'report':str(reports[-1])}))
