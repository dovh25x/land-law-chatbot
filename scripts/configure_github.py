"""Configure the authorized repository's Actions credentials without printing secrets."""
import base64
import json
import re

import httpx
from dotenv import dotenv_values


def main():
    try:
        from nacl.public import PublicKey, SealedBox
    except ImportError:
        raise SystemExit('Install operator dependency: pip install PyNaCl==1.6.2')
    env = dotenv_values('.env')
    repo = env.get('GITHUB_REPOSITORY', '').removeprefix('git@github.com:').removeprefix('https://github.com/').removesuffix('.git').rstrip('/')
    if repo != 'dovh25x/land-law-chatbot':
        raise SystemExit('This setup is scoped to dovh25x/land-law-chatbot')
    names = ['ADMIN_DATABASE_URL', 'GEMINI_API_KEY', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY',
             'BACKUP_ENCRYPTION_KEY', 'RENDER_API_KEY', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_AI_API_TOKEN']
    variables = {'RENDER_SERVICE_ID': env.get('RENDER_SERVICE_ID'),
                 'CLOUDFLARE_PAGES_PROJECT': env.get('CLOUDFLARE_PAGES_PROJECT'),
                 'API_BASE_URL': env.get('VITE_API_BASE_URL'),
                 'EMBEDDING_SEED_SHA256': env.get('EMBEDDING_SEED_SHA256'),
                 'EMBEDDING_PROVIDER': env.get('EMBEDDING_PROVIDER','gemini'),
                 'EMBEDDING_MODEL': env.get('EMBEDDING_MODEL','gemini-embedding-2'),
                 'EMBEDDING_DIMENSIONS': env.get('EMBEDDING_DIMENSIONS','768'),
                 'LLM_PROVIDER': env.get('LLM_PROVIDER','gemini'),
                 'GEMINI_MODEL': env.get('GEMINI_MODEL','gemini-3.8-flash'),
                 'CLOUDFLARE_LLM_MODEL': env.get('CLOUDFLARE_LLM_MODEL','@cf/qwen/qwen3-30b-a3b-fp8'),
                 'EMBEDDING_RESUME_ENABLED': 'true', 'MAINTENANCE_ENABLED': 'true'}
    if not env.get('GITHUB_TOKEN') or any(not env.get(n) for n in names) or any(not v for v in variables.values()):
        raise SystemExit('Missing operator credentials or checkpoint seed; configure .env first')
    if not re.fullmatch(r'[0-9a-f]{64}', variables['EMBEDDING_SEED_SHA256']):
        raise SystemExit('Invalid checkpoint seed checksum')
    root = f'/repos/{repo}/actions'
    with httpx.Client(base_url='https://api.github.com', timeout=30,
                      headers={'Authorization': 'Bearer '+env['GITHUB_TOKEN'],
                               'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}) as client:
        key = client.get(root+'/secrets/public-key')
        current = client.get(root+'/variables', params={'per_page': 100})
        if key.status_code != 200 or current.status_code != 200:
            raise SystemExit(f'No mutation: GitHub Secrets HTTP {key.status_code}; Variables HTTP {current.status_code}. Token needs Secrets and Variables read/write.')
        box = SealedBox(PublicKey(base64.b64decode(key.json()['key'])))
        existing = {v['name'] for v in current.json()['variables']}
        for name in names:
            encrypted = base64.b64encode(box.encrypt(env[name].encode())).decode()
            r = client.put(root+'/secrets/'+name, json={'encrypted_value': encrypted, 'key_id': key.json()['key_id']})
            if r.status_code not in (201, 204):
                raise SystemExit(f'Secret {name} configuration failed: HTTP {r.status_code}')
        # Enable scheduled jobs only after every credential and ordinary variable succeeds.
        for name, value in variables.items():
            r = (client.patch(root+'/variables/'+name, json={'name': name, 'value': value}) if name in existing
                 else client.post(root+'/variables', json={'name': name, 'value': value}))
            if r.status_code not in (201, 204):
                raise SystemExit(f'Variable {name} configuration failed: HTTP {r.status_code}')
    print(json.dumps({'repository': repo, 'secret_names': names, 'variable_names': list(variables),
                      'embedding_resume_enabled': True, 'maintenance_enabled': True}))


if __name__ == '__main__':
    main()
