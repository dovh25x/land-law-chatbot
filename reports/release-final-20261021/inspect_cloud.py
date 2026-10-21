"""Read-only cloud release gates. Never print env values, keys or DB URLs."""
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
from dotenv import dotenv_values

OUT=Path(__file__).parent


def database(values):
    try:
        with psycopg.connect(values['DATABASE_URL'],connect_timeout=10) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            rows=conn.execute("SELECT rolsuper,rolbypassrls,pg_has_role(current_user,'landlaw_runtime','member') FROM pg_roles WHERE rolname=current_user").fetchone()
            tables=[r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()]
            active=conn.execute("SELECT value FROM public.app_state WHERE key='active_release'").fetchone()
            role={'superuser':rows[0],'bypass_rls':rows[1],'member_landlaw_runtime':rows[2]}
            privileges={t:conn.execute('SELECT has_table_privilege(current_user,%s,%s)',('public.'+t,'INSERT')).fetchone()[0] for t in ('releases','source_reviews','messages','traces','answer_cache') if t in tables}
            return {'connected':True,'transaction':'READ ONLY','server_version':conn.info.server_version,
                'required_tables_present':{t:t in tables for t in ('releases','release_metadata','source_reviews','turns','chunks')},
                'active_corpus':active[0] if active else None,'role':role,'runtime_insert_privileges':privileges,
                'source_reviews':conn.execute('SELECT count(*) FROM public.source_reviews').fetchone()[0] if 'source_reviews' in tables else None}
    except Exception as error:
        return {'connected':False,'error_type':type(error).__name__}


async def main():
    values=dotenv_values('.env')
    result={'checked_at':datetime.now(UTC).isoformat(),'mutations':False,'external_llm_requests':0}
    async with httpx.AsyncClient(timeout=45) as client:
        response=await client.get('https://api.render.com/v1/services/'+values['RENDER_SERVICE_ID'],headers={'Authorization':'Bearer '+values['RENDER_API_KEY']})
        result['render']={'http_status':response.status_code}
        if response.status_code==200:
            service=response.json();details=service.get('serviceDetails',{})
            result['render'].update(plan=details.get('plan'),url=details.get('url'),branch=service.get('branch'),repo=service.get('repo'),auto_deploy_trigger=service.get('autoDeployTrigger'),type=service.get('type'))
        response=await client.get('https://api.render.com/v1/services/'+values['RENDER_SERVICE_ID']+'/env-vars',headers={'Authorization':'Bearer '+values['RENDER_API_KEY']})
        if response.status_code==200:
            env={row['envVar']['key']:row['envVar'].get('value') for row in response.json()}
            names=('GROQ_API_KEY','DATABASE_URL','INGRESS_SECRET','TURNSTILE_SECRET_KEY','IP_HASH_SECRET')
            result['render']['required_env_names_configured']={k:bool(env.get(k)) for k in names}
            result['render']['owner_connection_absent']=not bool(env.get('ADMIN_DATABASE_URL'))
            result['render']['secrets_match_local']={k:env.get(k)==values.get(k) for k in names if values.get(k)}
            result['render']['nonsecret_settings']={k:env.get(k) for k in ('APP_ENV','GROQ_MODEL','GENERATION_ENABLED','ALLOW_STALE_GENERATION','EMBEDDING_DIMENSIONS','PUBLIC_HOSTNAME')}
        response=await client.get('https://api.render.com/v1/services/'+values['RENDER_SERVICE_ID']+'/deploys?limit=5',headers={'Authorization':'Bearer '+values['RENDER_API_KEY']})
        if response.status_code==200:
            result['render']['recent_deploys']=[{'id':r['deploy']['id'],'status':r['deploy']['status'],'commit':r['deploy'].get('commit',{}).get('id'),'created_at':r['deploy'].get('createdAt')} for r in response.json()]
        response=await client.get(f"https://api.cloudflare.com/client/v4/accounts/{values['CLOUDFLARE_ACCOUNT_ID']}/pages/projects/{values['CLOUDFLARE_PAGES_PROJECT']}",headers={'Authorization':'Bearer '+values['CLOUDFLARE_API_TOKEN']})
        result['cloudflare']={'http_status':response.status_code}
        if response.status_code==200:
            project=response.json().get('result',{});env=project.get('deployment_configs',{}).get('production',{}).get('env_vars',{})
            result['cloudflare'].update(name=project.get('name'),subdomain=project.get('subdomain'),production_branch=project.get('production_branch'),domains=project.get('domains'),
                production_env_names=sorted(env),ingress_matches_local=env.get('INGRESS_SECRET',{}).get('value')==values.get('INGRESS_SECRET'),
                backend_origin_matches_render=env.get('BACKEND_ORIGIN',{}).get('value')==result['render'].get('url'))
        public='https://'+values.get('PUBLIC_HOSTNAME','hanoi-land-law.pages.dev')
        for path in ('/healthz','/readyz','/api/v1/status','/api/v1/evaluations/latest'):
            try:
                response=await client.get(public+path)
                data=response.json()
                allowed=('status','database','storage','corpus_release','generation_available','reason','source_gate','active_configuration_sha256','configuration_sha256','active_release','source_fresh')
                result.setdefault('public',{})[path]={'http_status':response.status_code,**{k:data[k] for k in allowed if k in data}}
            except Exception as error:
                result.setdefault('public',{})[path]={'error_type':type(error).__name__}
    result['postgresql']=await asyncio.to_thread(database,values)
    target=OUT/'cloud-inspection.json'
    if target.exists():
        raise ValueError('Preserve earlier cloud inspection')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


asyncio.run(main())
