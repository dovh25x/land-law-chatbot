import asyncio
import contextvars
import hashlib
import json
import re
import math
import statistics
import time
import uuid
from datetime import date, timedelta
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
    """Frozen displayed turns; never generated during scoring."""
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
                     "storage_backend": "postgresql" if settings.database_url.get_secret_value() else "sqlite",
                     "llm_budget": 6, "tool_budget": 12, "retrieval_rounds": 2}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()+b"".join(p.read_bytes() for p in files)).hexdigest()


async def evaluate(settings, store, provider, split="smoke", release_id=None, limit=None, concurrency=1, case_ids=None, modes=("agentic",)):
    if tuple(modes) != ('agentic',):
        raise ValueError('Only agentic evaluation is supported')
    if concurrency not in {1, 2}:
        raise ValueError('Evaluation concurrency must be one or two')
    cases, fingerprint = frozen_dataset(settings.data_dir, split)
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
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"as_of": str(local_date()), "configuration_sha256": configuration, "suite_sha256": fingerprint, "split": split, "storage_backend": "postgresql" if store.postgres else "sqlite"}
    json_write(metadata_path, metadata)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    attempts_path=records_path.parent/'attempts'
    for record in records:
        preserve_attempt(attempts_path,record,'imported_latest_checkpoint')
    agent = Agent(store, provider)
    case_label=contextvars.ContextVar('evaluation_case',default=None)
    generate=provider.generate
    generated_cases = set()
    async def capture_structured_output(schema,instruction,payload,budget):
        result=await generate(schema,instruction,payload,budget)
        label=case_label.get()
        if label and schema.__name__ == 'Draft':
            generated_cases.add(label)
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
        return {'case_id':case['id'],'mode':mode,
                'answer_origin': 'llm' if f"{case['id']}-{mode}" in generated_cases else 'deterministic',
                'result':result.model_dump(mode='json')}
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
    review_path = settings.data_dir / f'evaluation/{split}-reviews.json'
    report = summarise(records, cases, fingerprint, json.loads(review_path.read_text()) if review_path.exists() else {})
    report.update({"run_id": run_id, "release": release["id"], "model": provider.settings.generation_model,
                   "llm_provider": provider.settings.llm_provider,
                   "embedding_model": provider.settings.embedding_model, "split": split,
                   "corpus_embedded": release.get("embedded", False), "publication_candidate": False,
                   "notes": ["Technical regression evaluation; not independent legal certification."], **metadata})
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


def frozen_dataset(data_dir, split):
    if split not in {'smoke', 'supplemental'}:
        raise ValueError('Supported splits: smoke, supplemental')
    path = data_dir / 'evaluation' / f'{split}.jsonl'
    freeze_path = path.with_name('freeze.json') if split == 'smoke' else path.with_suffix('.freeze.json')
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = json.loads(freeze_path.read_text())
    cases = dataset(path)
    expected = 20 if split == 'smoke' else 4
    if (freeze.get('suite_sha256') != fingerprint or freeze.get('cases') != expected
            or len(cases) != expected or any(c.get('split') != split for c in cases)):
        raise ValueError('Evaluation suite freeze mismatch')
    return cases, fingerprint


def report_metrics(rows):
    """Descriptive statistics, with explicit denominators and missing telemetry."""
    groups = {}
    for name, statuses in {
        'answered': {'answered'}, 'clarification': {'clarification_needed'},
        'insufficient': {'insufficient_evidence'}, 'execution_failure': {'limited', 'error'},
    }.items():
        selected = [row for row in rows if row['status'] in statuses]
        groups[name] = {'cases': len(selected), **{
            verdict: sum(r.get('review') == verdict for r in selected)
            for verdict in ('pass', 'partial', 'fail', 'awaiting_review')}}
    usage = {}
    for key in ('elapsed_ms', 'token_usage', 'llm_calls', 'tool_calls'):
        values = [row['answer'][key] for row in rows if key in row.get('answer', {})]
        ordered = sorted(values)
        usage[key] = {'samples': len(values), 'total': sum(values),
                      'median': statistics.median(values) if values else None,
                      'p95': ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None}
    origins = {name: sum(row.get('answer_origin', 'unknown') == name for row in rows)
               for name in ('llm', 'deterministic', 'unknown')}
    gold_rows = [row for row in rows if row.get('gold_chunk_ids')]
    observed = [row for row in gold_rows if 'retrieved_chunk_ids' in row.get('answer', {})]
    hits = sum(bool(set(row['gold_chunk_ids']) & set(row['answer']['retrieved_chunk_ids'][:8]))
               for row in observed)
    return {'groups': groups, 'usage': usage, 'answer_origin': origins,
            'llm_used_cases': sum(row.get('answer', {}).get('llm_calls', 0) > 0 for row in rows),
            'evidence_hit_at_8': {'eligible_cases': len(gold_rows), 'measured_cases': len(observed),
                                 'hits': hits, 'rate': hits / len(observed) if observed else None,
                                 'scope': 'First eight agent evidence candidates; not a standalone retrieval benchmark.'},
            'scope': 'Descriptive single-run statistics; no SLA or overall legal accuracy claim.'}


async def evaluate_retrieval(settings, store, provider, split='smoke'):
    """Read-only hybrid retrieval evaluation; no generation or session writes."""
    cases, fingerprint = frozen_dataset(settings.data_dir, split)
    release = await asyncio.to_thread(store.release, None, True)
    if not release:
        raise ValueError('No corpus release to evaluate')
    rows = []
    for case in cases:
        if not case.get('gold_chunk_ids'):
            continue
        started = time.monotonic()
        vectors = await asyncio.to_thread(provider.local_embeddings.embed_many, [case['question']], None, True)
        vector = provider.normalize_vector(vectors[0], settings.embedding_dimensions)
        hits = await asyncio.to_thread(store.search, case['question'], vector, case.get('project'),
                                      release['id'], settings.embedding_model,
                                      date.fromisoformat(case['as_of']) if case.get('as_of') else local_date())
        ids = [item.chunk.id for item in hits[:8]]
        rows.append({'id': case['id'], 'has_history': bool(case.get('history')), 'gold_chunk_ids': case['gold_chunk_ids'], 'retrieved_chunk_ids': ids,
                     'hit': bool(set(ids) & set(case['gold_chunk_ids'])),
                     'elapsed_ms': round((time.monotonic() - started) * 1000)})
    report = {'checked_at': utcnow().isoformat(), 'split': split, 'suite_sha256': fingerprint,
              'release': release['id'], 'configuration_sha256': configuration_fingerprint(settings),
              'backend': 'postgresql' if store.postgres else 'sqlite', 'k': 8,
              'eligible_cases': len(rows), 'hits': sum(r['hit'] for r in rows),
              'hit_rate': sum(r['hit'] for r in rows) / len(rows) if rows else None,
              'generation_calls': 0, 'results': rows,
              'scope': 'Raw-question hybrid search without history rewriting, article routing or legal-relation expansion; any gold chunk in top 8 counts as a hit. Not legal answer accuracy.'}
    json_write(settings.reports_dir / 'retrieval' / f'{split}.json', report)
    return report
