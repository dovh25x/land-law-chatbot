"""Credential-safe deployment of existing services. Never creates paid resources."""
import json
import os
import subprocess
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}; configure .env or CI secrets")
    return value


def backend():
    token, service_id = required("RENDER_API_KEY"), required("RENDER_SERVICE_ID")
    commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    with httpx.Client(base_url="https://api.render.com/v1", timeout=30,
                      headers={"Authorization": f"Bearer {token}"}) as client:
        service = client.get(f"/services/{service_id}")
        if service.status_code != 200:
            raise SystemExit("Cannot inspect Render service")
        details = service.json().get("serviceDetails", {})
        if details.get("plan") != "free":
            raise SystemExit("Refusing deployment: Render service is not explicitly Free")
        response = client.post(f"/services/{service_id}/deploys", json={"clearCache": "do_not_clear","commitId":commit})
        if response.status_code not in (200, 201):
            raise SystemExit("Render deployment request failed")
        deploy_id = response.json()["id"]
        for _ in range(120):
            status = client.get(f"/services/{service_id}/deploys/{deploy_id}")
            if status.status_code != 200:
                raise SystemExit("Cannot inspect deployment status")
            value = status.json().get("status")
            if value == "live":
                if status.json().get("commit",{}).get("id")!=commit:
                    raise SystemExit("Deployed commit differs from tested checkout")
                print(json.dumps({"status": "live", "url": details.get("url"), "deploy_id": deploy_id,"source_commit":commit}))
                return
            if value in {"build_failed", "update_failed", "canceled", "deactivated"}:
                raise SystemExit(f"Render deployment ended: {value}")
            time.sleep(5)
    raise SystemExit("Deployment still pending; resume status check using the returned deployment in dashboard")


def frontend(preview=False):
    required("CLOUDFLARE_API_TOKEN"); required("CLOUDFLARE_ACCOUNT_ID")
    project = required("CLOUDFLARE_PAGES_PROJECT")
    api_url = '' if preview else required("VITE_API_BASE_URL")
    if not preview and api_url != 'https://'+project+'.pages.dev':
        raise SystemExit("Production frontend requires the canonical same-origin Pages API")
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True, env={**os.environ, 'VITE_API_BASE_URL': api_url})
    subprocess.run(["npx", "--yes", "wrangler@4", "pages", "deploy", "dist", "--project-name", project,
                    "--branch", "main"], cwd="frontend", check=True)


if __name__ == "__main__":
    if sys.argv[1] in {'backend', 'frontend'}:
        # Recompute evidence before credentials, network calls or a public write.
        from check_release_readiness import require_ready
        try:
            require_ready(required('RELEASE_READINESS_REPORT'))
        except (ValueError, OSError, KeyError, json.JSONDecodeError):
            raise SystemExit('Deployment blocked: complete current release-readiness evidence is required') from None
    {"backend": backend, "frontend": frontend, "frontend-preview": lambda: frontend(preview=True)}[sys.argv[1]]()
