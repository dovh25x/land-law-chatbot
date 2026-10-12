"""Configure only the user-selected Free Docker service; never print credentials."""
import json
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

from landlaw.config import Settings


def main():
    env, settings = dotenv_values('.env'), Settings()
    service_id, token = env.get('RENDER_SERVICE_ID'), env.get('RENDER_API_KEY')
    if not service_id or not token:
        raise SystemExit('Render service ID and API key required')
    origin = 'https://' + (env.get('CLOUDFLARE_PAGES_PROJECT') or 'hanoi-land-law') + '.pages.dev'
    desired = {'APP_ENV':'production','DATABASE_URL':settings.database_url.get_secret_value(),
        'GEMINI_API_KEY':settings.gemini_api_key.get_secret_value(),'IP_HASH_SECRET':settings.ip_hash_secret.get_secret_value(),
        'CORS_ORIGINS':origin,'GEMINI_MODEL':settings.gemini_model,'EMBEDDING_MODEL':settings.embedding_model,
        'LLM_PROVIDER':settings.llm_provider,'CLOUDFLARE_LLM_MODEL':settings.cloudflare_llm_model,
        'EMBEDDING_PROVIDER':settings.embedding_provider,'EMBEDDING_DIMENSIONS':str(settings.embedding_dimensions),
        'CLOUDFLARE_ACCOUNT_ID':settings.cloudflare_account_id,'CLOUDFLARE_AI_API_TOKEN':settings.cloudflare_ai_api_token.get_secret_value(),
        'TRUST_PROXY_HEADERS':'false','MAX_CONCURRENT_REQUESTS':'2','TURN_TIMEOUT_SECONDS':'90','SESSION_RETENTION_DAYS':'7'}
    Settings(_env_file=None,**{key.lower():value for key,value in desired.items()})
    with httpx.Client(base_url='https://api.render.com/v1',timeout=45,headers={'Authorization':'Bearer '+token}) as client:
        r = client.get('/services/'+service_id)
        if r.status_code != 200:
            raise SystemExit('Cannot inspect selected service')
        service = r.json()
        details = service.get('serviceDetails',{})
        if details.get('plan') != 'free' or details.get('runtime') != 'docker' or service.get('repo','').removesuffix('.git') != 'https://github.com/dovh25x/land-law-chatbot':
            raise SystemExit('Expected the authorized Free Docker service for this repository')
        r = client.get(f'/services/{service_id}/env-vars?limit=100')
        if r.status_code != 200:
            raise SystemExit('Cannot inspect service environment')
        current = {item['envVar']['key']:item['envVar']['value'] for item in r.json()}
        for key in ('GLOBAL_DAILY_LLM_LIMIT','GLOBAL_DAILY_EMBEDDING_LIMIT','GLOBAL_DAILY_EMBEDDING_ITEM_LIMIT'):
            current.pop(key, None)
        current.update(desired)
        r = client.put(f'/services/{service_id}/env-vars',json=[{'key':k,'value':v} for k,v in current.items()])
        if r.status_code not in (200,201):
            raise SystemExit(f'Environment update failed: HTTP {r.status_code}')
        r = client.patch('/services/'+service_id,json={'autoDeployTrigger':'off','serviceDetails':{'healthCheckPath':'/healthz'}})
        if r.status_code != 200:
            raise SystemExit(f'Health-check update failed: HTTP {r.status_code}')
        set_key('.env','VITE_API_BASE_URL',details['url'])
        set_key('.env','CORS_ORIGINS',origin)
        report = {'frontend':origin,'backend':details['url'],'render_service_id':service_id,'render_plan':'free',
            'runtime':'docker','health_check':'/healthz','configured_environment_keys':sorted(desired),
            'corpus_published':False,'acceptance_passed':False}
        Path('reports/cloud-resources.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
