import asyncio
import contextvars
import hashlib
import json
import re
import time
import uuid
from datetime import timedelta
from pathlib import Path

from .agent import Agent
from .ingest import json_write
from .models import ChatRequest
from .security import local_date, new_token, utcnow


def dataset(path: Path):
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({q["id"] for q in cases}) != len(cases):
        raise ValueError("Duplicate benchmark IDs")
    for case in cases:
        validate_history(case.get('history', []))
    return cases


def validate_history(history):
    """Frozen displayed turns, shared by both modes; never generated during scoring."""
    if not isinstance(history, list) or len(history) > 8:
        raise ValueError('Benchmark history must contain at most eight fixed turns')
    for index, turn in enumerate(history):
        if (not isinstance(turn, dict) or turn.get('role') != ('user' if index % 2 == 0 else 'assistant')
                or not isinstance(turn.get('content'), str) or not 1 <= len(turn['content']) <= 3000):
            raise ValueError('Benchmark history requires alternating user/assistant content fixtures')
    if len(history) % 2:
        raise ValueError('Benchmark history must end with a fixed assistant turn')


def seed_history(store, session_id, history):
    """Write explicitly labelled fixtures only into the evaluator's private session."""
    validate_history(history)
    now = utcnow()
    with store.transaction() as conn:
        for index, turn in enumerate(history):
            payload = {**turn, 'benchmark_fixture': True}
            payload.pop('role')
            store.execute(conn, 'INSERT INTO messages VALUES(?,?,?,?,?)',
                (str(uuid.uuid4()), session_id, turn['role'], json.dumps(payload, ensure_ascii=False),
                 (now + timedelta(microseconds=index)).isoformat()))


def preserve_attempt(folder,record,origin='executed'):
    """Keep immutable results before replacing a failed resumable checkpoint."""
    checksum=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    path=folder/f'{checksum}.json'
    if not path.exists():
        json_write(path,{'recorded_at':utcnow().isoformat(),'origin':origin,'record':record})
    return path


def configuration_fingerprint(settings):
    files = [Path(__file__).with_name(name) for name in ("agent.py", "provider.py", "embedding.py", "local_embedding.py", "store.py", "retrieval.py", "config.py", "publication.py", "models.py", "security.py", "api.py")]
    configuration = {"model": settings.generation_model, "llm_provider": settings.llm_provider, "embedding_model": settings.embedding_model,
                     "dimensions": settings.embedding_dimensions, 'embedding_provider':settings.embedding_provider,
                     "timeout_seconds": settings.turn_timeout_seconds,
                     "llm_budget": 6, "tool_budget": 12, "retrieval_rounds": 2}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()+b"".join(p.read_bytes() for p in files)).hexdigest()


async def evaluate(settings, store, provider, split="smoke", release_id=None, limit=None, concurrency=1, case_ids=None, modes=("agentic",)):
    if split != 'smoke' or tuple(modes) != ('agentic',):
        raise ValueError('Only the twenty-case academic agentic suite is supported')
    if concurrency not in {1,2}:
        raise ValueError('Evaluation concurrency must be one or two')
    path = settings.data_dir / ('evaluation/smoke.jsonl' if split=='smoke' else 'evaluation/questions.jsonl')
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze=json.loads(path.with_name('freeze.json').read_text())
    if freeze.get('suite_sha256') != fingerprint or freeze.get('cases') != 20:
        raise ValueError('Academic suite freeze mismatch')
    cases = [c for c in dataset(path) if c["split"] == split]
    if len(cases) != 20:raise ValueError('Exactly twenty cases are required')
    if not provider.configured:
        raise ValueError("Cannot evaluate without the selected provider API key")
    release = store.release(release_id, metadata_only=True)
    if not release:
        raise ValueError("No corpus release to evaluate")
    configuration = configuration_fingerprint(settings)
    run_id = f"{release['id']}-{provider.settings.generation_model.replace('/', '_')}-{split}-{fingerprint[:8]}-{configuration[:8]}-c{concurrency}"
    run_id += '-agentic'
    records_path = settings.reports_dir / "runs" / run_id / "records.json"
    metadata_path = records_path.with_name("metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"as_of": str(local_date()), "configuration_sha256": configuration}
    json_write(metadata_path, metadata)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    attempts_path=records_path.parent/'attempts'
    for record in records:
        preserve_attempt(attempts_path,record,'imported_latest_checkpoint')
    agent = Agent(store, provider)
    case_label=contextvars.ContextVar('evaluation_case',default=None)
    generate=provider.generate
    async def capture_structured_output(schema,instruction,payload,budget):
        result=await generate(schema,instruction,payload,budget)
        label=case_label.get()
        if label and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',label):
            output=result.model_dump(mode='json')
            checksum=hashlib.sha256(json.dumps(output,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            json_write(records_path.parent/'model_outputs'/f'{label}-{budget.llm_calls}-{checksum[:16]}.json',
                {'scope':'Unverified structured model output for developer diagnosis; never delivered as a chatbot answer. No hidden reasoning.',
                 'schema':schema.__name__,'case_mode':label,'llm_calls':budget.llm_calls,'output':output})
        return result
    provider.generate=capture_structured_output
    provider_ready_at=0.0
    async def observe_provider_capacity(response):
        nonlocal provider_ready_at
        if response.request.url.host!='api.groq.com':return
        if response.status_code==400:
            await response.aread()
            try:code=response.json().get('error',{}).get('code')
            except (ValueError,AttributeError):code=None
            print(json.dumps({'evaluation_provider_format_error':code if code in
                {'tool_use_failed','json_validate_failed'} else 'other'}),flush=True)
        if response.status_code==429:
            await response.aread()
            try:
                message=response.json().get('error',{}).get('message','')
            except (ValueError,AttributeError):message=''
            # Extract only numeric quota telemetry; the provider body may echo
            # prompts or identify an account and must never enter public logs.
            scope=re.search(r'\b(TPD|TPM|RPD|RPM)\b',message)
            usage={name.lower():int(value) for name,value in re.findall(
                r'\b(Limit|Used|Requested):?\s*(\d+)\b',message,re.IGNORECASE)}
            print(json.dumps({'evaluation_provider_quota':{
                'scope':scope[0] if scope else 'unspecified',**usage}}),flush=True)
        try:
            remaining=int(response.headers['x-ratelimit-remaining-tokens'])
            capacity=int(response.headers['x-ratelimit-limit-tokens'])
        except (KeyError,ValueError):return
        reset=response.headers.get('x-ratelimit-reset-tokens','')
        duration=re.fullmatch(r'(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?',reset)
        if not duration:return
        seconds=float(duration[1] or 0)*60+float(duration[2] or 0)
        # Use only provider-reported free capacity, never an application quota.
        # Start the next benchmark turn after its token bucket recovers so
        # retry requests do not consume that turn's six-call workflow budget.
        provider_ready_at=time.monotonic()+seconds if remaining<min(7000,capacity*.85) else 0
    if settings.llm_provider=='groq':
        provider.client.event_hooks.setdefault('response',[]).append(observe_provider_capacity)
    async def emit(_):
        pass
    pending = [(case,mode) for case in cases for mode in modes
        if not any(r['case_id']==case['id'] and r['mode']==mode and r['result']['status'] not in {'limited','error'} for r in records)]
    if case_ids is not None:
        if not set(case_ids)<={c['id'] for c in cases}:
            raise ValueError('Unknown evaluation case ID')
        # Execute a prioritized subset while keeping the original full suite,
        # dataset checksum and uncompleted cases in the report denominator.
        pending=[(case,mode) for case,mode in pending if case['id'] in case_ids]
    if limit is not None:
        pending=pending[:limit]
    async def execute(case,mode):
        session_id = str(uuid.uuid4())
        await asyncio.to_thread(store.create_session,session_id,new_token())
        await asyncio.to_thread(seed_history, store, session_id, case.get('history', []))
        label_token=case_label.set(f"{case['id']}-{mode}")
        try:
            result = await agent.run(ChatRequest(session_id=session_id,message=case['question'],
                project=case.get('project'),as_of=case.get('as_of') or metadata['as_of'],mode=mode),emit,release['id'])
        finally:case_label.reset(label_token)
        return {'case_id':case['id'],'mode':mode,'result':result.model_dump(mode='json')}
    for start in range(0,len(pending),concurrency):
        cooldown=provider_ready_at-time.monotonic()
        if cooldown>0:
            print(json.dumps({'evaluation_provider_cooldown_seconds':round(cooldown,2)}),flush=True)
            await asyncio.sleep(cooldown)
        results=await asyncio.gather(*(execute(c,m) for c,m in pending[start:start+concurrency]))
        for result in results:
            preserve_attempt(attempts_path,result)
            records=[r for r in records if not (r['case_id']==result['case_id'] and r['mode']==result['mode'])]
            records.append(result)
            json_write(records_path,records)
            print(json.dumps({'evaluation_progress':{'case_id':result['case_id'],'mode':result['mode'],
                'status':result['result']['status'],'elapsed_ms':result['result']['elapsed_ms'],
                'llm_calls':result['result']['llm_calls'],'checkpoint_records':len(records)}},ensure_ascii=False),flush=True)
        if any(r['result']['status'] in {'limited','error'} for r in results):
            break
    review_path = settings.data_dir / ('evaluation/smoke-reviews.json' if split=='smoke' else 'evaluation/reviews.json')
    report = summarise(records, cases, fingerprint, json.loads(review_path.read_text()) if review_path.exists() else {})
    report.update({"run_id": run_id, "release": release["id"], "model": provider.settings.generation_model,
                   "llm_provider": provider.settings.llm_provider,
                   "embedding_model": provider.settings.embedding_model, "split": split,
                   "corpus_embedded": release.get("embedded", False), "publication_candidate": False,
                   "notes": ["Academic evaluation only; not independent legal certification."], **metadata})
    report['execution_modes'] = list(modes)
    report['execution_concurrency'] = concurrency
    attempts=[json.loads(p.read_text()) for p in attempts_path.glob('*.json')]
    report['attempt_history']={'attempts':len(attempts),'retry_attempts':len(attempts)-len(records),
        'limited_or_error_attempts':sum(a['record']['result']['status'] in {'limited','error'} for a in attempts),
        'scope':'Every new attempt is retained; legacy checkpoints imported as latest results only.',
        'directory':str(attempts_path)}
    report['acceptance_passed'] = False
    report['latency_scope'] = f'CLI run, modes {list(modes)}, concurrency {concurrency}; provider-reported cooldown between turns excluded. Public API single-user p95 measured separately.'
    json_write(records_path.with_name('summary.json'),report)
    report=public_report(report)
    json_write(settings.reports_dir / ('smoke.json' if split=='smoke' else 'latest.json'), report)
    from html import escape
    html = "<!doctype html><html lang='vi'><meta charset='utf-8'><title>Benchmark</title>"
    html += "<style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px}pre{white-space:pre-wrap}</style>"
    html += "<h1>Báo cáo benchmark</h1><p>Kết quả chưa rà soát chưa chứng nhận chất lượng pháp lý.</p><pre>" + escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>"
    (settings.reports_dir / ('smoke.html' if split=='smoke' else 'benchmark.html')).write_text(html, encoding="utf-8")
    return report


def summarise(records, cases, fingerprint, reviews=None):
    items=[r for r in records if r['mode']=='agentic']
    return {'status':'awaiting_review','dataset_sha256':fingerprint,'generated_at':utcnow().isoformat(),
            'cases':len(cases),'acceptance_passed':False,
            'results':[{'mode':'agentic','completed':len(items),'reviewed':0,
                        'llm_calls':sum(r['result']['llm_calls'] for r in items),
                        'limited_or_error':sum(r['result']['status'] in {'limited','error'} for r in items)}]}


def public_report(report):
    return {**report,'acceptance_passed':False,'quality_metrics_status':'awaiting_review'}
