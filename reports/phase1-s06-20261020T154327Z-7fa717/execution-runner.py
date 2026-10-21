"""One authorized S06 invocation; diagnostic observers never alter model inputs/verdicts."""
import asyncio
import hashlib
import json
import sys
import uuid
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from scripts.evaluate_generation_candidate import main
from landlaw.agent import Agent
from landlaw.provider import GroqProvider

ROOT = Path.cwd()
OUT = ROOT / 'reports' / ('phase1-s06-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6])
OUT.mkdir(exist_ok=False)
QUESTION = 'Theo Điều 95 Luật Đất đai 2024, giấy chứng nhận có phải là điều kiện duy nhất để được bồi thường về đất không?'
BACKUP = Path('data/staging/production-backup-check-20261020/corpus-backup.json')
COOLDOWN = Path('reports/production-finalization-20261020/final-quality-evaluation/operator-cooldown.json')
protected = sorted(set(list(Path('backend/landlaw').glob('*.py')) + list(Path('tests').glob('test_*.py')) + list(Path('data/evaluation').rglob('*')) + [BACKUP, Path('data/staging/production-backup-check-20261020/release.json')]))
protected = [p for p in protected if p.is_file()]
def hashes():
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
def write(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
baseline = hashes()
write('protected-inputs-before.json', baseline)
inherited = json.loads(COOLDOWN.read_text())
write('operator-cooldown.json', inherited)
write('execution-scope.json', {
    'case_ids': ['S06'], 'split': 'smoke', 'as_of': '2024-08-02',
    'question': QUESTION, 'storage_backend': 'isolated temporary sqlite',
    'max_api_requests_including_retries': 6, 'max_turn_seconds': 90,
    'inherited_cooldown': inherited, 'automatic_case_rerun': False,
    'observers': 'Public request JSON (no headers), numeric usage, retrieved legal passages and exact verifier verdict; inputs and return values unchanged.'})

original_init = GroqProvider.__init__
original_usage = GroqProvider.record_usage
original_tools = Agent.tools
original_verify = Agent.verify
wire_count = 0
tools_count = 0
verify_count = 0
usage_events = []

def observed_init(self, settings, store, *args, **kwargs):
    original_init(self, settings, store, *args, **kwargs)
    assert not store.postgres and not settings.database_url.get_secret_value()
    assert not settings.admin_database_url.get_secret_value()
    assert settings.llm_provider == 'groq' and settings.generation_model == 'openai/gpt-oss-120b'
    assert settings.turn_timeout_seconds <= 90
    secrets = [getattr(settings, key).get_secret_value() for key in
               ('groq_api_key', 'backup_encryption_key', 'ip_hash_secret', 'ingress_secret', 'turnstile_secret_key')]
    async def observe_request(request):
        global wire_count
        assert request.url.host == 'api.groq.com'
        body = json.loads(request.content)
        payload = json.loads(body['messages'][-1]['content'])
        assert body['model'] == settings.generation_model
        assert body['response_format']['json_schema']['name'] in {'Draft', 'Verification'}
        assert payload.get('question') == QUESTION and not payload.get('history')
        evidence = payload.get('evidence', [])
        assert 1 <= len(evidence) <= 6
        assert all(item.get('document_id') == 'luat-dat-dai-2024'
                   and item.get('locator', '').split(' · ')[0] == 'Điều 95' for item in evidence)
        assert not any(key in payload for key in ('catalogue', 'catalogue_fields'))
        serialized = json.dumps(body, ensure_ascii=False)
        assert not any(secret and secret in serialized for secret in secrets)
        assert wire_count < 6
        wire_count += 1
        write(f'wire/requests/{wire_count:02d}.json', body)
    async def observe_response(response):
        await response.aread()
        try:
            decoded = response.json()
        except ValueError:
            decoded = {}
        # Never persist raw provider errors, account identifiers or hidden reasoning.
        write(f'wire/responses/{wire_count:02d}.json', {
            'status_code': response.status_code,
            'usage': decoded.get('usage', {}),
            'retry_after': response.headers.get('retry-after'),
            'rate_limits': {key: value for key, value in response.headers.items() if key.startswith('x-ratelimit-')},
            'schema': json.loads(response.request.content)['response_format']['json_schema']['name'],
        })
    self.client.event_hooks.setdefault('request', []).append(observe_request)
    self.client.event_hooks.setdefault('response', []).append(observe_response)

async def observed_usage(self, kind, units=1):
    result = await original_usage(self, kind, units)
    usage_events.append({'scope': self.usage_scope, 'kind': kind, 'units': units})
    write('usage-events.json', usage_events)
    return result

def passages(state):
    return [{'chunk_id': item.chunk.id, 'document_id': item.document.id,
             'document_number': item.document.document_number, 'locator': item.chunk.locator,
             'page': item.chunk.page, 'checksum': item.chunk.checksum,
             'text': item.chunk.text, 'applicability': item.applicability}
            for item in state.get('evidence', [])]

async def observed_tools(self, state):
    global tools_count
    result = await original_tools(self, state)
    tools_count += 1
    write(f'retrieval/{tools_count:02d}.json', {'round': result.get('rounds'), 'evidence': passages(result)})
    return result

async def observed_verify(self, state):
    global verify_count
    result = await original_verify(self, state)
    verify_count += 1
    write(f'verification/{verify_count:02d}.json', {
        'draft': result['draft'].model_dump(mode='json'),
        'verdict': result['verification'].model_dump(mode='json'),
        'llm_calls': result['budget'].llm_calls})
    return result

GroqProvider.__init__ = observed_init
GroqProvider.record_usage = observed_usage
Agent.tools = observed_tools
Agent.verify = observed_verify

print(json.dumps({'artifact_directory': str(OUT), 'authorized_case': 'S06'}), flush=True)
error_type = None
try:
    asyncio.run(main(Namespace(backup=BACKUP, output=OUT, split=['smoke'], resume=True,
                             postgres=False, case_id=['S06'], no_generation=False)))
except Exception as error:
    error_type = type(error).__name__
finally:
    after = hashes()
    write('protected-inputs-after.json', after)
    write('execution-receipt.json', {'wire_requests': wire_count,
          'retrieval_observations': tools_count, 'verification_observations': verify_count,
          'protected_inputs_unchanged': after == baseline, 'error_type': error_type})
    print(json.dumps({'wire_requests': wire_count, 'protected_inputs_unchanged': after == baseline,
                      'error_type': error_type, 'artifact_directory': str(OUT)}), flush=True)
if error_type or after != baseline:
    raise SystemExit(1)
