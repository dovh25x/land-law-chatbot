"""Live infrastructure checks before legal-corpus publication; never certifies acceptance."""
import json
from pathlib import Path

import httpx
from dotenv import dotenv_values

from landlaw.security import utcnow


def main():
    env = dotenv_values('.env')
    base = env['VITE_API_BASE_URL'].rstrip('/')
    origin = 'https://' + env.get('CLOUDFLARE_PAGES_PROJECT','hanoi-land-law') + '.pages.dev'
    checks = {}
    with httpx.Client(timeout=180) as client:
        health = client.get(base+'/healthz')
        checks['health_https'] = health.status_code == 200 and health.json().get('status') == 'ok'
        ready = client.get(base+'/readyz')
        readiness = ready.json()
        checks['database_connected'] = readiness.get('database') is True
        checks['readiness_honest'] = ready.status_code == (200 if readiness.get('corpus_release') else 503)
        checks['ai_configured'] = readiness.get('llm_configured') is True
        checks['no_public_draft_corpus'] = bool(readiness.get('corpus_release')) or not client.get(base+'/api/v1/documents').json()['documents']
        checks['three_project_profiles'] = len(client.get(base+'/api/v1/projects').json()['projects']) == 3
        cors = client.options(base+'/api/v1/chat',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
        checks['cors_frontend'] = cors.status_code == 200 and cors.headers.get('access-control-allow-origin') == origin
        blocked = client.options(base+'/api/v1/chat',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'})
        checks['cors_untrusted_blocked'] = 'access-control-allow-origin' not in blocked.headers
        first, second = [client.post(base+'/api/v1/sessions').json() for _ in range(2)]
        sid = first['session_id']
        path = base+f'/api/v1/sessions/{sid}/messages'
        auth = {'Authorization':'Bearer '+first['token']}
        checks['session_auth'] = client.get(path,headers=auth).status_code == 200
        checks['session_isolation'] = client.get(path,headers={'Authorization':'Bearer '+second['token']}).status_code == 404
        response = client.post(base+'/api/v1/chat',headers={**auth,'Origin':origin},json={'session_id':sid,'message':'Cần kiểm tra căn cứ nào về bồi thường khi thu hồi đất tại Hà Nội?','mode':'agentic'})
        checks['sse_transport'] = response.status_code == 200 and response.headers.get('content-type','').startswith('text/event-stream')
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
        answer = next((e for e in events if 'trace_id' in e),{})
        checks['real_generation'] = answer.get('llm_calls',0) >= 1
        checks['verified_or_explicit_limit'] = answer.get('status') in {'answered','clarification_needed','insufficient_evidence'}
        checks['history_persisted'] = len(client.get(path,headers=auth).json()['messages']) == 2
        if not readiness.get('corpus_release'):
            checks['unpublished_corpus_abstention'] = answer.get('status') == 'insufficient_evidence' and not answer.get('citations')
        report = {'checked_at':utcnow().isoformat(),'base_url':base,'frontend':origin,'passed':all(checks.values()),
            'checks':checks,'answer_status':answer.get('status'),'llm_calls':answer.get('llm_calls'),
            'elapsed_ms':answer.get('elapsed_ms'),'trace_id':answer.get('trace_id'),
            'corpus_published':bool(readiness.get('corpus_release')),'acceptance_passed':False,
            'scope':'infrastructure smoke only; legal demo requires published reviewed corpus and fixed acceptance benchmark'}
        Path('reports/infrastructure-smoke.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        if not report['passed']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
