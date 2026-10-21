"""Read historical receipts and serialize a proposed request without any HTTP.

This is budget arithmetic, not a C01/C02 model attempt or a generated answer.
Never refunds the two old errors merely because they lack usage metadata.
"""
import ast
import asyncio
import hashlib
import json
import tempfile
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.models import Draft
from landlaw.provider import GroqProvider, SYSTEM_BOUNDARY
from landlaw.request_budget import BudgetExceeded, RequestBudget
from landlaw.store import Store

OUT = Path(__file__).parent
PRIOR = Path('reports/phase3a-live-20261021T070325Z')


class CapturedWithoutIO(Exception):
    pass


async def run():
    settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
        groq_api_key='offline-placeholder', allow_stale_generation=False)
    fingerprint = configuration_fingerprint(settings)
    ledger = RequestBudget(path=OUT / 'prior-allocation-ledger.json', identity=fingerprint)
    assert not ledger.entries, 'This arithmetic probe is single-use; preserve prior output'
    for p in sorted(PRIOR.glob('C01/wire/*/request.json')):
        request = json.loads(p.read_text())
        response_path = p.with_name('response.json')
        response = json.loads(response_path.read_text())
        entry = ledger.reserve(request)
        ledger.settle(entry, response.get('usage', {}), status_code=response['status_code'], headers=response['headers'])
        ledger.entries[entry]['historical_receipt'] = {
            'request_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'response_sha256': hashlib.sha256(response_path.read_bytes()).hexdigest(),
            'source_runtime_fingerprint': json.loads((PRIOR / 'configuration-lock.json').read_text())['runtime_fingerprint']}
        ledger.persist()
    prior = ledger.summary()
    assert prior['confirmed_usage'] == 4829 and prior['estimated_usage'] == 47330
    payloads = json.loads(Path('reports/phase2d-synthesis-20261021/acceptance-locked/report.json').read_text())
    payload = next(r['synthesis_payload'] for r in payloads['cases'] if r['id'] == 'C02')
    instructions = [ast.literal_eval(node.args[1]) for node in ast.walk(ast.parse(Path('backend/landlaw/agent.py').read_text()))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'generate'
        and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == 'Draft']
    assert len(instructions) == 1
    captured = {}
    class NoIOClient:
        async def post(self, url, *, headers, json):
            captured.update(json)  # Authorization headers deliberately discarded.
            raise CapturedWithoutIO
        async def aclose(self):
            pass
    with tempfile.TemporaryDirectory(prefix='landlaw-phase3b-serialization-') as folder:
        store = Store(settings.model_copy(update={'sqlite_path': str(Path(folder) / 'test.db')}))
        provider = GroqProvider(settings, store, client=NoIOClient())
        try:
            try:
                await provider._groq_generate(Draft, {
                    'systemInstruction': {'parts': [{'text': SYSTEM_BOUNDARY + instructions[0]}]},
                    'contents': [{'parts': [{'text': json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}]}],
                    'generationConfig': {'claimPolicy': payload.get('claim_policy')}})
            except CapturedWithoutIO:
                pass
        finally:
            await provider.close()
            store.close()
    wire_bytes = len(json.dumps(captured, ensure_ascii=False, separators=(',', ':')).encode())
    required = wire_bytes + 4096 + captured['max_completion_tokens']
    try:
        ledger.reserve(captured)
    except BudgetExceeded:
        allowed = False
    else:
        allowed = True
    report = {'phase3a_allocation_hard_cap': 60000, 'before_proposed_request': prior,
        'proposed_case': 'C02', 'proposed_initial_request_wire_bytes': wire_bytes,
        'required_reservation': required, 'would_exceed_original_allocation': not allowed,
        'request_allowed_under_carried_budget': allowed,
        'new_external_model_requests': 0, 'new_confirmed_usage': 0,
        'runtime_fingerprint_for_proposed_request': fingerprint,
        'scope': 'Read saved receipts; no case execution, model, HTTP, corpus mutation or quota query. '
            'No new 60000-token allocation is implied by a new report/output directory. '
            'Unknown reservations remain charged; a smaller reservation requires a proven tokenizer/framing bound.'}
    (OUT / 'prior-allocation-check.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


asyncio.run(run())
