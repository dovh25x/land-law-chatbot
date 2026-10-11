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
    with httpx.Client(base_url="https://api.render.com/v1", timeout=30,
                      headers={"Authorization": f"Bearer {token}"}) as client:
        service = client.get(f"/services/{service_id}")
        if service.status_code != 200:
            raise SystemExit("Cannot inspect Render service")
        details = service.json().get("serviceDetails", {})
        if details.get("plan") != "free":
            raise SystemExit("Refusing deployment: Render service is not explicitly Free")
        response = client.post(f"/services/{service_id}/deploys", json={"clearCache": "do_not_clear"})
        if response.status_code not in (200, 201):
            raise SystemExit("Render deployment request failed")
        deploy_id = response.json()["id"]
        for _ in range(120):
            status = client.get(f"/services/{service_id}/deploys/{deploy_id}")
            if status.status_code != 200:
                raise SystemExit("Cannot inspect deployment status")
            value = status.json().get("status")
            if value == "live":
                print(json.dumps({"status": "live", "url": details.get("url"), "deploy_id": deploy_id}))
                return
            if value in {"build_failed", "update_failed", "canceled", "deactivated"}:
                raise SystemExit(f"Render deployment ended: {value}")
            time.sleep(5)
    raise SystemExit("Deployment still pending; resume status check using the returned deployment in dashboard")


def frontend():
    required("CLOUDFLARE_API_TOKEN"); required("CLOUDFLARE_ACCOUNT_ID")
    project = required("CLOUDFLARE_PAGES_PROJECT")
    api_url = required("VITE_API_BASE_URL")
    if not api_url.startswith("https://") or not api_url.endswith(".onrender.com"):
        raise SystemExit("Production frontend requires an HTTPS Render URL allowed by CSP")
    subprocess.run(["npm", "run", "build"], cwd="frontend", check=True)
    subprocess.run(["npx", "--yes", "wrangler@4", "pages", "deploy", "frontend/dist", "--project-name", project,
                    "--branch", "main"], check=True)


if __name__ == "__main__":
    {"backend": backend, "frontend": frontend}[sys.argv[1]]()
