"""Verify the published demo over HTTPS; never print/store session credentials.

Uses public-law questions only. This is operational evidence, not the fixed
acceptance benchmark or independent legal certification.
"""
import json
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.security import utcnow


def main():
    env=dotenv_values('.env')
    base=env['VITE_API_BASE_URL'].rstrip('/')
    if base!='https://land-law-chatbot.onrender.com':
        raise SystemExit('This live check is scoped to the authorized Render service')
    origin='https://hanoi-land-law.pages.dev'
    checks={}
    answers=[]
    with httpx.Client(timeout=180) as client:
        health=client.get(base+'/healthz')
        checks['health_https']=health.status_code==200
        ready=client.get(base+'/readyz')
        readiness=ready.json()
        checks['published_hybrid_ready']=ready.status_code==200 and readiness.get('retrieval_mode')=='hybrid'
        if not checks['published_hybrid_ready']:
            raise SystemExit('No published hybrid release; live legal verification deferred')
        checks['honest_quality_label']=readiness.get('publication_profile') in {'technical_demo','demo'} and readiness.get('quality_status')=='acceptance_pending'
        documents=client.get(base+'/api/v1/documents').json()['documents']
        checks['minimum_legal_documents']=sum(d['source_kind']=='legal' for d in documents)>=30
        checks['three_project_source_sets']=all(sum(d.get('project')==p for d in documents)>=5 for p in ('ring4','songhong','olympic'))
        checks['three_project_profiles']=len(client.get(base+'/api/v1/projects').json()['projects'])==3
        evaluation=client.get(base+'/api/v1/evaluations/latest').json()
        checks['active_configuration_matches']=evaluation.get('active_configuration_sha256')==configuration_fingerprint(Settings())
        checks['no_false_acceptance']=not evaluation.get('acceptance_valid_for_active')
        cors=client.options(base+'/api/v1/chat',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
        checks['cors_frontend']=cors.status_code==200 and cors.headers.get('access-control-allow-origin')==origin
        first,other=[client.post(base+'/api/v1/sessions').json() for _ in range(2)]
        path=base+f"/api/v1/sessions/{first['session_id']}/messages"
        auth={'Authorization':'Bearer '+first['token']}
        checks['session_isolation']=client.get(path,headers={'Authorization':'Bearer '+other['token']}).status_code==404
        for mode in ('baseline','agentic'):
            started=time.monotonic()
            with client.stream('POST',base+'/api/v1/chat',headers={**auth,'Origin':origin},json={
                'session_id':first['session_id'],'message':'Điều 104 Luật Đất đai 2024 quy định bồi thường chi phí di chuyển tài sản như thế nào?',
                'as_of':'2024-08-02','mode':mode}) as response:
                response.raise_for_status()
                checks[f'{mode}_sse_transport']=response.headers.get('content-type','').startswith('text/event-stream')
                events=[]
                for line in response.iter_lines():
                    if line.startswith('data: '):events.append(json.loads(line[6:]))
            answer=next((e for e in events if 'trace_id' in e),{})
            checks[f'{mode}_real_grounded_answer']=bool(answer.get('status')=='answered' and answer.get('citations')
                and answer.get('llm_calls',0)>=2 and answer.get('model')==Settings().generation_model
                and answer.get('corpus_release')==readiness['corpus_release'])
            checks[f'{mode}_verification_precedes_result']=any(e.get('step')=='verification' for e in events[:events.index(answer)]) if answer else False
            checks[f'{mode}_no_draft_content_in_progress']=all('content' not in e for e in events if 'step' in e)
            trace_path=base+f"/api/v1/sessions/{first['session_id']}/traces/{answer.get('trace_id','missing')}"
            checks[f'{mode}_trace_authenticated']=client.get(trace_path,headers=auth).status_code==200
            checks[f'{mode}_trace_isolated']=client.get(trace_path,headers={'Authorization':'Bearer '+other['token']}).status_code==404
            for citation in answer.get('citations',[]):
                source=client.get(base+'/api/v1/documents/'+citation['document_id'],params={'locator':citation['locator']})
                checks[f"{mode}_citation_{citation['id']}"]=source.status_code==200 and any(
                    c['id']==citation['id'] and c['text']==citation['excerpt'] for c in source.json()['document']['chunks'])
            answers.append({'mode':mode,'status':answer.get('status'),'model':answer.get('model'),
                'elapsed_ms':answer.get('elapsed_ms'),'https_seconds':round(time.monotonic()-started,3),
                'llm_calls':answer.get('llm_calls'),'trace_id':answer.get('trace_id'),
                'verified_claims':answer.get('verified_claims',[]),'citations':answer.get('citations',[])})
            print(json.dumps({'live_answer_mode':mode,'status':answer.get('status')},ensure_ascii=False),flush=True)
        checks['history_persisted']=len(client.get(path,headers=auth).json()['messages'])==4
    report={'checked_at':utcnow().isoformat(),'base_url':base,'frontend':origin,'passed':all(checks.values()),
        'release':readiness['corpus_release'],'configuration_sha256':configuration_fingerprint(Settings()),
        'publication_profile':readiness.get('publication_profile'),'acceptance_passed':False,
        'checks':checks,'answers':answers,
        'scope':'Two uncached real HTTPS legal answers plus source/trace/session checks; no acceptance or p95 claim.'}
    Path('reports/live-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='answers'},ensure_ascii=False,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':
    main()
