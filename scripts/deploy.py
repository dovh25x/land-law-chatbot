"""Credential-safe deployment of existing services. Never creates paid resources."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}; configure .env or CI secrets")
    return value


def resolve_source_commit(requested=None):
    commit = requested or os.environ.get('DEPLOY_SOURCE_COMMIT') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Deployment requires a full commit SHA')
    actual=subprocess.check_output(['git','rev-parse','--verify',commit+'^{commit}'],text=True).strip()
    if actual != commit or subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],capture_output=True).returncode:
        raise ValueError('Deployment commit must be in the current checkout history')
    changed=subprocess.check_output(['git','diff','--name-only',commit],text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
    if any(not (p.startswith(('reports/','docs/')) or p=='README.md') for p in changed+untracked):
        raise ValueError('Commit application changes before deployment')
    return commit


def preflight(requested=None):
    commit=resolve_source_commit(requested)
    # Model scoring remains available explicitly; never fabricate a passing report.
    if os.environ.get('REQUIRE_QUALITY_READINESS','false').lower()=='true':
        try:
            from scripts.check_release_readiness import require_ready
        except ModuleNotFoundError:
            from check_release_readiness import require_ready
        result=require_ready(required('RELEASE_READINESS_REPORT'))
        if result['source_commit']!=commit:
            raise ValueError('Quality evidence targets another commit')
    return commit


def backend(tested_commit=None, deployment_id=None, receipt=None):
    token, service_id = required("RENDER_API_KEY"), required("RENDER_SERVICE_ID")
    commit=tested_commit or subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    with httpx.Client(base_url="https://api.render.com/v1", timeout=30,
                      headers={"Authorization": f"Bearer {token}"}) as client:
        service = client.get(f"/services/{service_id}")
        if service.status_code != 200:
            raise SystemExit("Cannot inspect Render service")
        details = service.json().get("serviceDetails", {})
        if details.get("plan") != "free":
            raise SystemExit("Refusing deployment: Render service is not explicitly Free")
        if service.json().get('autoDeployTrigger')!='off':
            raise SystemExit('Disable Render auto-deploy to preserve the selected SHA')
        receipt=Path(receipt or f"reports/deployments/render-{uuid.uuid4().hex}.jsonl")
        receipt.parent.mkdir(parents=True,exist_ok=True)
        def record(value):
            value={'checked_at':datetime.now(timezone.utc).isoformat(),'source_commit':commit,**value}
            with receipt.open('a') as output:output.write(json.dumps(value)+'\n')
            print(json.dumps({**value,'receipt':str(receipt)}),flush=True)
        if deployment_id:
            deploy_id=deployment_id
        else:
            response = client.post(f"/services/{service_id}/deploys", json={"clearCache": "do_not_clear","commitId":commit})
            if response.status_code not in (200, 201, 202):
                raise SystemExit("Render deployment request failed")
            deploy_id = response.json()["id"]
        record({'status':'monitoring','deploy_id':deploy_id})
        previous=None
        for _ in range(120):
            status = client.get(f"/services/{service_id}/deploys/{deploy_id}")
            if status.status_code != 200:
                raise SystemExit("Cannot inspect deployment status")
            value = status.json().get("status")
            if value != previous:
                record({'status':value,'deploy_id':deploy_id});previous=value
            if value == "live":
                if status.json().get("commit",{}).get("id")!=commit:
                    raise SystemExit("Deployed commit differs from tested checkout")
                record({'status':'verified','url':details.get('url'),'deploy_id':deploy_id})
                return
            if value in {"build_failed", "update_failed", "canceled", "deactivated"}:
                raise SystemExit(f"Render deployment ended: {value}")
            time.sleep(5)
    raise SystemExit(f"Deployment pending; resume using --deployment-id {deploy_id}; receipt {receipt}")


def frontend(preview=False, tested_commit=None):
    required("CLOUDFLARE_API_TOKEN"); required("CLOUDFLARE_ACCOUNT_ID")
    project = required("CLOUDFLARE_PAGES_PROJECT")
    api_url = '' if preview else required("VITE_API_BASE_URL")
    if not preview and api_url != 'https://'+project+'.pages.dev':
        raise SystemExit("Production frontend requires the canonical same-origin Pages API")
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True, env={**os.environ, 'VITE_API_BASE_URL': api_url})
    command=["npx", "--yes", "wrangler@4", "pages", "deploy", "dist", "--project-name", project,
             "--branch", "preview" if preview else "main"]
    if tested_commit:command.extend(['--commit-hash',tested_commit])
    subprocess.run(command, cwd="frontend", check=True)


if __name__ == "__main__":
    load_dotenv()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',choices=('backend','frontend','frontend-preview'))
    parser.add_argument('--commit')
    parser.add_argument('--deployment-id',help='Resume monitoring an existing Render deployment; do not create another')
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args()
    try:tested_commit=preflight(args.commit)
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as error:
        raise SystemExit('Deployment source preflight failed: '+type(error).__name__) from None
    if args.target=='backend':backend(tested_commit,args.deployment_id,args.receipt)
    else:frontend(preview=args.target=='frontend-preview',tested_commit=tested_commit)
