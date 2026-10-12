"""Create dedicated free resources. Do not modify unrelated services or enable billing."""
import json
import secrets
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

from landlaw.config import Settings


def main():
    env = dotenv_values('.env')
    settings = Settings()
    required = ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'RENDER_API_KEY')
    if any(not env.get(key) for key in required):
        raise SystemExit('Missing cloud credentials in .env')
    project = env.get('CLOUDFLARE_PAGES_PROJECT') or 'hanoi-land-law'
    if project != 'hanoi-land-law':
        raise SystemExit('Review the configured project before provisioning a different name')
    origin = f'https://{project}.pages.dev'
    if not settings.ip_hash_secret.get_secret_value():
        set_key('.env', 'IP_HASH_SECRET', secrets.token_hex(32))
        settings = Settings()
    with httpx.Client(timeout=45) as client:
        cf_headers = {'Authorization': f"Bearer {env['CLOUDFLARE_API_TOKEN']}"}
        root = f"https://api.cloudflare.com/client/v4/accounts/{env['CLOUDFLARE_ACCOUNT_ID']}/pages/projects"
        response = client.get(root + '/' + project, headers=cf_headers)
        if response.status_code == 404:
            response = client.post(root, headers=cf_headers, json={'name': project, 'production_branch': 'main'})
        if response.status_code >= 400 or not response.json().get('success'):
            raise SystemExit(f'Cloudflare Pages provisioning failed: HTTP {response.status_code}')
        set_key('.env', 'CLOUDFLARE_PAGES_PROJECT', project)
        render_headers = {'Authorization': f"Bearer {env['RENDER_API_KEY']}"}
        response = client.get('https://api.render.com/v1/owners', headers=render_headers)
        if response.status_code != 200 or len(response.json()) != 1:
            raise SystemExit('Select a Render workspace explicitly; expected one accessible workspace')
        owner_id = response.json()[0]['owner']['id']
        services = client.get('https://api.render.com/v1/services?limit=100', headers=render_headers)
        if services.status_code != 200:
            raise SystemExit('Cannot inspect existing Render services')
        matches = [item['service'] for item in services.json() if item['service']['name'] == 'hanoi-land-law-api']
        if not matches:
            # Supplying plan explicitly is essential: Render's omitted default is paid.
            body = {'type': 'web_service', 'name': 'hanoi-land-law-api', 'ownerId': owner_id,
                    'repo': 'https://github.com/dovh25x/land-law-chatbot.git', 'branch': 'main', 'autoDeployTrigger': 'off',
                    'serviceDetails': {'runtime': 'docker', 'plan': 'free', 'region': 'singapore', 'numInstances': 1,
                                       'healthCheckPath': '/healthz', 'envSpecificDetails': {'dockerContext': '.', 'dockerfilePath': './Dockerfile'}},
                    'envVars': [{'key': key, 'value': value} for key, value in {
                        'APP_ENV': 'production', 'DATABASE_URL': settings.database_url.get_secret_value(),
                        'GEMINI_API_KEY': settings.gemini_api_key.get_secret_value(), 'IP_HASH_SECRET': settings.ip_hash_secret.get_secret_value(),
                        'CORS_ORIGINS': origin, 'GEMINI_MODEL': settings.gemini_model, 'EMBEDDING_MODEL': settings.embedding_model,
                        'EMBEDDING_PROVIDER':settings.embedding_provider,'EMBEDDING_DIMENSIONS':str(settings.embedding_dimensions),
                        'CLOUDFLARE_AI_API_TOKEN':settings.cloudflare_ai_api_token.get_secret_value(),'CLOUDFLARE_ACCOUNT_ID':settings.cloudflare_account_id,
                        'TRUST_PROXY_HEADERS': 'false'}.items()]}
            response = client.post('https://api.render.com/v1/services', headers=render_headers, json=body)
            if response.status_code not in (200, 201):
                message = str(response.json().get('message', ''))
                for value in env.values():
                    if value and len(value) >= 12:
                        message = message.replace(value, '[REDACTED]')
                raise SystemExit(f'Render Free creation failed: HTTP {response.status_code}; {message[:250]}; no upgrade attempted')
            result = response.json()
            service = result.get('service', result)
        else:
            service = matches[0]
        if service.get('serviceDetails', {}).get('plan') != 'free':
            raise SystemExit('Refusing a non-Free Render service')
        service_id, url = service['id'], service['serviceDetails']['url']
        set_key('.env', 'RENDER_SERVICE_ID', service_id)
        set_key('.env', 'VITE_API_BASE_URL', url)
        set_key('.env', 'CORS_ORIGINS', origin)
        report = {'frontend': origin, 'backend': url, 'render_service_id': service_id, 'render_plan': 'free',
                  'corpus_published': False, 'acceptance_passed': False}
        Path('reports/cloud-resources.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))


if __name__ == '__main__':
    main()
