import asyncio
import contextvars
import hashlib
import json
import math
import re
import statistics
import time
import uuid
from datetime import timedelta
from pathlib import Path

from .agent import Agent
from .ingest import json_write
from .models import ChatRequest
from .security import digest, local_date, new_token, official_url, utcnow


def dataset(path: Path):
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({q["id"] for q in cases}) != len(cases):
        raise ValueError("Duplicate benchmark IDs")
    for case in cases:
        validate_history(case.get('history', []))
    return cases


def validate_frozen_benchmark(path, freeze_path, sources_path, store=None, release_id=None):
    """Check immutable source references; this cannot certify legal correctness."""
    cases = dataset(path)
    freeze = json.loads(freeze_path.read_text())
    sources = json.loads(sources_path.read_text())
    acceptance = [case for case in cases if case['split'] == 'acceptance']
    if (len(cases) != 120 or len(acceptance) != 80
            or sum(case['split'] == 'dev' for case in cases) != 40
            or digest(path.read_bytes()) != freeze['dataset_sha256']
            or digest(json.dumps(acceptance, ensure_ascii=False, sort_keys=True)) != freeze['acceptance_sha256']
            or digest(sources_path.read_bytes()) != freeze['gold_sources_sha256']
            or [case['id'] for case in acceptance] != freeze['acceptance_ids']):
        raise ValueError('Benchmark freeze mismatch; create a reviewed new version before evaluation')
    passages = sources['passages']
    checked = set()
    for case in cases:
        if (case.get('ground_truth_status') != 'source_checked' or not case.get('source_review')
                or not case.get('rubric') or not case.get('source_review_metadata', {}).get('reviewed_at')):
            raise ValueError('Unreviewed benchmark case')
        refs = {ref['chunk_id']: ref for ref in case.get('reference_chunks', [])}
        if set(case.get('gold_chunk_ids', [])) != set(refs):
            raise ValueError('Gold IDs do not match source references')
        for cid, ref in refs.items():
            source = passages.get(cid)
            if (not source or not official_url(ref['url'])
                    or any(source.get(key) != value for key, value in ref.items())
                    or digest(source['text']) != ref['chunk_checksum']):
                raise ValueError('Invalid benchmark source provenance or checksum')
            if store is not None and cid not in checked:
                chunk = store.chunk(cid, release_id)
                document = store.document(ref['document_id'], release_id)
                if (not chunk or not document or chunk.document_id != ref['document_id']
                        or chunk.checksum != ref['chunk_checksum'] or chunk.locator != ref['locator']
                        or chunk.page != ref['page'] or document.checksum != ref['document_checksum']):
                    raise ValueError('Benchmark source differs from evaluation corpus')
            checked.add(cid)
    return {'dataset_sha256': freeze['dataset_sha256'], 'acceptance_cases': 80,
            'source_checked_cases': 120, 'distinct_source_passages': len(checked),
            'independent_legal_certification': False, 'freeze_sha256': digest(freeze_path.read_bytes())}


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


def summarise(records, cases, fingerprint, reviews=None):
    reviews, by_id = reviews or {}, {c["id"]: c for c in cases}
    summary = {"status": "awaiting_review", "dataset_sha256": fingerprint, "generated_at": utcnow().isoformat(),
               "cases": len(cases), "completed_pairs": 0, "results": [], "acceptance_passed": False}
    for mode in ("baseline", "agentic"):
        items = [r for r in records if r["mode"] == mode]
        latencies, recalls, scores, support = [], [], [], []
        critical_failed, reviewed, valid, unsupported = [], 0, 0, 0
        review_notes_complete = True
        for item in items:
            case, result = by_id[item["case_id"]], item["result"]
            result_hash = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            review = reviews.get(f"{item['case_id']}:{mode}:{result_hash}")
            if result["status"] not in {"limited", "error"}:
                latencies.append(result["elapsed_ms"] / 1000)
            gold = case.get("gold_chunk_ids", [])
            if case.get("ground_truth_status") == "source_checked" and gold:
                recalls.append(len(set(result.get("retrieved_chunk_ids", [])[:8]) & set(gold))/len(set(gold)))
            cited = [c["id"] for c in result.get("citations", [])]
            if all(c in result.get("evidence_chunk_ids", []) for c in cited):
                valid += 1
            if review and case.get("ground_truth_status") == "source_checked":
                reviewed += 1
                scores.append(bool(review.get("passed")))
                support.extend(review.get("claim_support", []))
                unsupported += sum(not value for value in review.get('claim_support', []))
                review_notes_complete &= bool(review.get('source_checked') and review.get('notes')
                    and len(review.get('claim_support', [])) == len(result.get('verified_claims', [])))
                if case.get("critical") and not review.get("passed"):
                    critical_failed.append(case["id"])
        p95 = sorted(latencies)[math.ceil(len(latencies)*.95)-1] if latencies else None
        summary["results"].append({"mode": mode, "completed": len(items), "reviewed": reviewed,
            "recall_at_8": statistics.mean(recalls) if recalls else None,
            "answer_pass_rate": statistics.mean(scores) if scores else None,
            "citation_id_valid_rate": valid/len(items) if items else None,
            "claim_support_rate": statistics.mean(support) if support else None,
            "unsupported_claims": unsupported, "source_review_complete": reviewed == len(cases) and review_notes_complete,
            "p95_seconds": p95, "llm_calls": sum(r["result"]["llm_calls"] for r in items),
            "embedding_calls": sum(r['result'].get('embedding_calls',0) for r in items),
            "tool_calls": sum(r["result"]["tool_calls"] for r in items), "critical_failed": critical_failed,
            "limited_or_error": sum(r["result"]["status"] in {"limited", "error"} for r in items)})
    summary["completed_pairs"] = sum(all(any(r["case_id"] == c["id"] and r["mode"] == m for r in records)
                                         for m in ("baseline", "agentic")) for c in cases)
    agent = summary["results"][1]
    if agent["reviewed"] == len(cases) and summary["completed_pairs"] == len(cases) and agent["recall_at_8"] is not None:
        summary["status"] = "reviewed"
        summary["acceptance_passed"] = bool(agent["answer_pass_rate"] >= .85 and agent["recall_at_8"] >= .85
            and agent["citation_id_valid_rate"] == 1 and (agent["claim_support_rate"] or 0) >= .95
            and not agent["critical_failed"] and not agent["limited_or_error"] and (agent["p95_seconds"] or 999) <= 60)
    return summary


def configuration_fingerprint(settings):
    files = [Path(__file__).with_name(name) for name in ("agent.py", "provider.py", "embedding.py", "local_embedding.py", "store.py", "config.py", "publication.py", "models.py", "security.py", "api.py")]
    configuration = {"model": settings.generation_model, "llm_provider": settings.llm_provider, "embedding_model": settings.embedding_model,
                     "dimensions": settings.embedding_dimensions, 'embedding_provider':settings.embedding_provider,
                     "timeout_seconds": settings.turn_timeout_seconds,
                     "llm_budget": 6, "tool_budget": 12, "retrieval_rounds": 2}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()+b"".join(p.read_bytes() for p in files)).hexdigest()


def public_report(report):
    """Keep progress public; publish quality rates only after both modes are reviewed."""
    public=json.loads(json.dumps(report))
    complete=bool(public.get('cases') and public.get('completed_pairs')==public['cases']
        and {r.get('mode') for r in public.get('results',[])}=={'baseline','agentic'}
        and all(r.get('reviewed')==public['cases'] and r.get('source_review_complete')
                for r in public['results']))
    public['quality_metrics_status']='reviewed' if complete else 'withheld_pending_full_source_review'
    if not complete:
        public['acceptance_passed']=False
        for row in public.get('results',[]):
            for field in ('recall_at_8','answer_pass_rate','citation_id_valid_rate','claim_support_rate','unsupported_claims'):
                row[field]=None
    return public


async def evaluate(settings, store, provider, split="dev", release_id=None, limit=None, concurrency=2):
    if concurrency not in {1,2}:
        raise ValueError('Evaluation concurrency must be one or two')
    path = settings.data_dir / ('evaluation/smoke.jsonl' if split=='smoke' else 'evaluation/questions.jsonl')
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    cases = [c for c in dataset(path) if c["split"] == split]
    if not provider.configured:
        raise ValueError("Cannot evaluate without real GEMINI_API_KEY")
    release = store.release(release_id, metadata_only=True)
    if not release:
        raise ValueError("No corpus release to evaluate")
    source_validation = None
    if split == 'acceptance':
        source_validation = await asyncio.to_thread(validate_frozen_benchmark, path,
            path.with_name('acceptance-freeze.json'), path.with_name('gold-sources.json'), store, release['id'])
    configuration = configuration_fingerprint(settings)
    run_id = f"{release['id']}-{provider.settings.generation_model.replace('/', '_')}-{split}-{fingerprint[:8]}-{configuration[:8]}-c{concurrency}"
    records_path = settings.reports_dir / "runs" / run_id / "records.json"
    metadata_path = records_path.with_name("metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"as_of": str(local_date()), "configuration_sha256": configuration}
    if source_validation:
        metadata['benchmark_source_validation'] = source_validation
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
    pending = [(case,mode) for case in cases for mode in ('baseline','agentic')
        if not any(r['case_id']==case['id'] and r['mode']==mode and r['result']['status'] not in {'limited','error'} for r in records)]
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
                   "notes": ["Development runs on incomplete staging cannot certify acceptance; query embedding failures fall back to lexical retrieval."], **metadata})
    report['execution_concurrency'] = concurrency
    attempts=[json.loads(p.read_text()) for p in attempts_path.glob('*.json')]
    report['attempt_history']={'attempts':len(attempts),'retry_attempts':len(attempts)-len(records),
        'limited_or_error_attempts':sum(a['record']['result']['status'] in {'limited','error'} for a in attempts),
        'scope':'Every new attempt is retained; legacy checkpoints imported as latest results only.',
        'directory':str(attempts_path)}
    report['acceptance_passed'] = bool(report['acceptance_passed'] and split=='acceptance'
        and len(cases)==80 and all(c.get('ground_truth_status')=='source_checked' for c in cases)
        and all(r['reviewed']==80 and r['source_review_complete'] for r in report['results']))
    report['latency_scope'] = f'Paired CLI run, concurrency {concurrency}; provider-reported cooldown between turns excluded. Public API single-user p95 measured separately.'
    for name in ('source-audit','runtime-tests'):
        evidence_path = settings.reports_dir/f'{name}.json'
        evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
        field = name.replace('-','_')
        report[field+'_passed'] = bool(evidence.get('passed') and evidence.get('release')==release['id']
            and (name=='source-audit' or evidence.get('configuration_sha256')==configuration))
        report[field+'_sha256'] = hashlib.sha256(evidence_path.read_bytes()).hexdigest() if evidence_path.exists() else None
    json_write(records_path.with_name('summary.json'),report)
    report=public_report(report)
    json_write(settings.reports_dir / ('smoke.json' if split=='smoke' else 'latest.json'), report)
    from html import escape
    html = "<!doctype html><html lang='vi'><meta charset='utf-8'><title>Benchmark</title>"
    html += "<style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px}pre{white-space:pre-wrap}</style>"
    html += "<h1>Báo cáo benchmark</h1><p>Kết quả chưa rà soát chưa chứng nhận chất lượng pháp lý.</p><pre>" + escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>"
    (settings.reports_dir / ('smoke.html' if split=='smoke' else 'benchmark.html')).write_text(html, encoding="utf-8")
    return report
