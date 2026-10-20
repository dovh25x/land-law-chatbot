import hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
import httpx,psycopg
from dotenv import dotenv_values
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint

def main():
    expected_commit=sys.argv[1]
    assert re.fullmatch('[a-f0-9]{40}',expected_commit)
    v=dotenv_values('.env');root=Path('reports/production-readiness-20261020')
    settings=Settings();fingerprint=configuration_fingerprint(settings)
    assert settings.database_url.get_secret_value()
    receipt={'checked_at':datetime.now(timezone.utc).isoformat(),'source_commit':expected_commit,
             'expected_configuration_sha256':fingerprint,'read_only_database':True}
    with httpx.Client(timeout=90,follow_redirects=False) as c:
        render=c.get(f"https://api.render.com/v1/services/{v['RENDER_SERVICE_ID']}",headers={'Authorization':'Bearer '+v['RENDER_API_KEY']})
        render.raise_for_status();service=render.json();details=service['serviceDetails']
        assert details['plan']=='free' and service['autoDeployTrigger']=='off'
        r=c.get(f"https://api.render.com/v1/services/{v['RENDER_SERVICE_ID']}/deploys?limit=1",headers={'Authorization':'Bearer '+v['RENDER_API_KEY']});r.raise_for_status()
        deployment=r.json()[0]['deploy'];assert deployment['status']=='live' and deployment['commit']['id']==expected_commit
        receipt['render']={'plan':'free','auto_deploy':'off','deploy_id':deployment['id'],'status':'live','commit':deployment['commit']['id']}
        r=c.get(f"https://api.cloudflare.com/client/v4/accounts/{v['CLOUDFLARE_ACCOUNT_ID']}/pages/projects/{v['CLOUDFLARE_PAGES_PROJECT']}",headers={'Authorization':'Bearer '+v['CLOUDFLARE_API_TOKEN']});r.raise_for_status()
        project=r.json()['result'];pages=project.get('canonical_deployment') or project['latest_deployment']
        assert pages['environment']=='production' and pages['latest_stage']['status']=='success'
        assert pages['deployment_trigger']['metadata']['commit_hash']==expected_commit
        receipt['pages']={'project':project['name'],'deploy_id':pages['id'],'environment':pages['environment'],'commit':expected_commit,'status':pages['latest_stage']['status']}
        base='https://hanoi-land-law.pages.dev'
        for path in ['/readyz','/api/v1/status','/api/v1/evaluations/latest']:
            r=c.get(base+path);r.raise_for_status();value=r.json()
            if path.endswith('latest'):
                assert value['active_configuration_sha256']==fingerprint
                value={k:value.get(k) for k in ['active_release','active_configuration_sha256','matches_active_configuration','matches_active_release','default_run_id']}
            receipt[path]=value
        ready=receipt['/readyz'];status=receipt['/api/v1/status']
        assert ready['status']=='ready' and ready['database'] and ready['storage']=='postgresql'
        assert ready['corpus_release']=='corpus-a26bc99e541fbbe2'
        assert ready['publication_profile']=='academic' and ready['quality_status']=='academic_prototype'
        assert status['api_version']==3 and status['capabilities']=={'citizen_answers':True,'answer_schema_version':2}
        assert status['corpus_release']==ready['corpus_release']
        r=c.get(base+'/api/v1/documents');r.raise_for_status();catalog=r.json()
        assert len(catalog['documents'])==60 and all(d.get('project') in (None,'ring4') for d in catalog['documents'])
        candidate_ids=['hanoi-1132-2025-procedure','hanoi-reception-calendar','hanoi-reception-relocation-2026']
        for identifier in candidate_ids:
            r=c.get(base+'/api/v1/documents/'+identifier);r.raise_for_status();d=r.json()['document']
            assert d['availability']=='reference_only' and d['chunks']==[] and d['applicability_verified'] is False
        receipt['catalog']={'documents':60,'references':len(catalog['references']),'candidate_reference_only_ids':candidate_ids,'ring4_scope':True}
        direct=c.get(details['url']+'/api/v1/status')
        assert direct.status_code==403 and direct.json()['detail']['code']=='untrusted_ingress'
        receipt['signed_ingress']={'public_api':200,'direct_unsigned_api':403}
        r=c.get(base);r.raise_for_status()
        assets=re.findall(r'<script[^>]+src="([^"]+)"',r.text);assert assets
        bundles=[]
        for asset in assets:
            local=Path('frontend/dist')/asset.lstrip('/');assert local.is_file()
            remote=c.get(base+asset);remote.raise_for_status()
            assert hashlib.sha256(remote.content).digest()==hashlib.sha256(local.read_bytes()).digest()
            bundles.append({'path':asset,'sha256':hashlib.sha256(remote.content).hexdigest()})
        receipt['frontend_bundles']=bundles
    with psycopg.connect(v['DATABASE_URL'],connect_timeout=15) as connection:
        connection.read_only=True
        with connection.cursor() as cursor:
            cursor.execute("SELECT value FROM public.app_state WHERE key='active_release'");assert cursor.fetchone()[0]==ready['corpus_release']
            privileges={}
            for table in ['messages','traces','answer_cache']:
                cursor.execute("SELECT has_table_privilege(current_user,%s,'SELECT'),has_table_privilege(current_user,%s,'INSERT')",('public.'+table,'public.'+table))
                read,write=cursor.fetchone();assert not read and not write;privileges[table]={'select':read,'insert':write}
            cursor.execute('SELECT DISTINCT vector_dims(embedding) FROM public.chunks WHERE release_id=%s',(ready['corpus_release'],));assert cursor.fetchall()==[(384,)]
            cursor.execute('SELECT count(*) FROM public.chunks WHERE release_id=%s',(ready['corpus_release'],));assert cursor.fetchone()[0]==7392
        receipt['database']={'runtime_connection_only':True,'active_corpus_matches':True,'embedding_dimensions':384,'chunks':7392,'history_privileges':privileges,'conversation_payloads_read':False}
    receipt['passed']=True
    output=root/'production-identity.json';assert not output.exists()
    output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':True,'receipt':str(output),'source_commit':expected_commit,'configuration_sha256':fingerprint}))

try:main()
except Exception as error:
    print(json.dumps({'passed':False,'error_type':type(error).__name__}));raise SystemExit(1) from None
