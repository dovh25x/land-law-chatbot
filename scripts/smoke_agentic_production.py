"""Minimal real production smoke for Agentic RAG over the public Pages ingress.

Uses the same public endpoints as the browser (Pages Function signs the Render
request). No retries; each turn is a real provider request that counts against
the approved release allocation. Only synthetic questions are sent.
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import httpx


def parse_sse(response):
    events = []
    event = None
    data = []
    for line in response.iter_lines():
        if line.startswith('event:'):
            event = line.split(':', 1)[1].strip()
        elif line.startswith('data:'):
            data.append(line.split(':', 1)[1].strip())
        elif not line.strip():
            if event is not None:
                payload = '\n'.join(data)
                try:
                    events.append((event, json.loads(payload) if payload else {}))
                except ValueError:
                    events.append((event, {'raw': payload[:500]}))
            event, data = None, []
    return events


def chat(client, base_url, session_id, token, message):
    started = time.monotonic()
    response = client.post(
        f'{base_url}/api/v1/chat',
        headers={'Authorization': f'Bearer {token}'},
        json={'session_id': session_id, 'message': message, 'project': 'ring4',
              'mode': 'agentic_rag', 'request_id': str(uuid.uuid4()), 'history': []})
    response.raise_for_status()
    events = parse_sse(response)
    result = next((payload for name, payload in events if name == 'result'), None)
    failure = next((payload for name, payload in events if name == 'failure'), None)
    progress = [payload for name, payload in events if name == 'progress']
    return {'elapsed_ms': int((time.monotonic() - started) * 1000),
            'events': [name for name, _ in events], 'result': result, 'failure': failure,
            'progress_steps': [item.get('step') for item in progress if isinstance(item, dict)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='https://hanoi-land-law.pages.dev')
    parser.add_argument('--output', default='reports/evaluation/agentic-rag-final/production-smoke.json')
    args = parser.parse_args()
    report = {'base_url': args.base_url, 'turns': []}
    with httpx.Client(timeout=180, follow_redirects=False) as client:
        status = client.get(f'{args.base_url}/api/v1/status')
        report['status_http'] = status.status_code
        report['status'] = status.json() if status.status_code == 200 else status.text[:300]
        session = client.post(f'{args.base_url}/api/v1/sessions')
        report['session_http'] = session.status_code
        if session.status_code != 201:
            report['session_error'] = session.text[:300]
            Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            sys.exit(1)
        payload = session.json()
        session_id, token = payload['session_id'], payload['token']
        for label, message in [
            ('social', 'Xin chào'),
            ('legal-L02', 'Tôi không có Giấy chứng nhận nhưng có quyết định giao đất thì có được bồi thường không?'),
        ]:
            try:
                turn = chat(client, args.base_url, session_id, token, message)
            except Exception as exc:
                turn = {'error': f'{type(exc).__name__}: {exc}'}
            turn['label'] = label
            report['turns'].append(turn)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({turn['label']: {
        'http_error': turn.get('error'),
        'status': (turn.get('result') or {}).get('status'),
        'mode': (turn.get('result') or {}).get('mode'),
        'llm_calls': (turn.get('result') or {}).get('llm_calls'),
        'tool_calls': (turn.get('result') or {}).get('tool_calls'),
        'citations': len((turn.get('result') or {}).get('citations') or []),
    } for turn in report['turns']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
