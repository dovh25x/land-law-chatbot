"""Set only approved non-secret serving flags; no credential rotation or plan change."""
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

OUT=Path(__file__).parent
values=dotenv_values('.env')
assert json.loads((OUT/'rollback-restore.json').read_text())['status']=='PASS'
assert json.loads((OUT/'qa/source-lookup-pg-acceptance.json').read_text())['status']=='PASS'
target=OUT/'safe-render-configuration.json'
if target.exists():
    raise ValueError('Preserve configuration receipt; do not silently repeat')
with httpx.Client(base_url='https://api.render.com/v1',timeout=30,
    headers={'Authorization':'Bearer '+values['RENDER_API_KEY']}) as client:
    base='/services/'+values['RENDER_SERVICE_ID']
    response=client.get(base)
    assert response.status_code==200
    service=response.json()
    assert service['serviceDetails']['plan']=='free' and service.get('autoDeployTrigger')=='off'
    flags={'GENERATION_ENABLED':'false','SOURCE_LOOKUP_ONLY':'true','ALLOW_STALE_GENERATION':'false'}
    statuses={}
    for key,value in flags.items():
        response=client.put(base+'/env-vars/'+key,json={'value':value})
        statuses[key]=response.status_code
        if response.status_code!=200:
            break
    receipt={'checked_at':datetime.now(UTC).isoformat(),'status':'PASS' if all(statuses.get(k)==200 for k in flags) else 'INCOMPLETE',
        'nonsecret_flags':flags,'http_statuses':statuses,'credentials_changed':False,'plan_changed':False,
        'deploy_triggered':False,'requires_new_deploy_to_apply':True,
        'documentation':'https://api-docs.render.com/reference/update-env-var',
        'rollback_policy':'Keep generation false/allow_stale false even on old source; do not restore unsafe flags.'}
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    assert receipt['status']=='PASS'
