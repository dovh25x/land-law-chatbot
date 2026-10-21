"""Negative public ingress test: no challenge token, session or model call."""
import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values


def main(output):
    if output.exists():
        raise ValueError('Preserve prior ingress evidence')
    values=dotenv_values('.env')
    public='https://'+values.get('PUBLIC_HOSTNAME','hanoi-land-law.pages.dev')
    backend=values.get('BACKEND_ORIGIN','https://land-law-chatbot.onrender.com')
    with httpx.Client(timeout=60) as client:
        edge=client.post(public+'/api/v1/sessions',json={})
        direct=client.post(backend+'/api/v1/sessions',json={})
        def code(response):
            try:
                detail=response.json().get('detail',{})
                return detail.get('code') if isinstance(detail,dict) else 'nonstructured_detail'
            except ValueError:
                return 'non_json'
        record={'checked_at':datetime.now(UTC).isoformat(),'edge_http_status':edge.status_code,'edge_error_code':code(edge),
            'unsigned_backend_http_status':direct.status_code,'unsigned_backend_error_code':code(direct),
            'signed_ingress_observed':edge.status_code==400 and code(edge)=='challenge_required',
            'unsigned_request_rejected':direct.status_code==403 and code(direct)=='untrusted_ingress',
            'human_turnstile_pass':'NOT_TESTED','session_created':False,'external_llm_requests':0,
            'scope':'Missing-token negative probe, not CAPTCHA bypass or a successful public chat.'}
        output.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(record))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
