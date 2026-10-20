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



def preserve_attempt(folder,record,origin='executed'):
    """Keep immutable results before replacing a failed resumable checkpoint."""
    checksum=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    path=folder/f'{checksum}.json'
    if not path.exists():
        json_write(path,{'recorded_at':utcnow().isoformat(),'origin':origin,'record':record})
    return path


def configuration_fingerprint(settings):
    files = [Path(__file__).with_name(name) for name in ("agent.py", "provider.py", "embedding.py", "local_embedding.py", "store.py", "retrieval.py", "config.py", "publication.py", "models.py", "security.py", "api.py", "catalog.py", "citizen.py", "ops.py")]
    configuration = {"model": settings.generation_model, "llm_provider": settings.llm_provider, "embedding_model": settings.embedding_model,
                     "dimensions": settings.embedding_dimensions, 'embedding_provider':settings.embedding_provider,
                     "timeout_seconds": settings.turn_timeout_seconds,
                     "allow_stale_generation": settings.allow_stale_generation,
                     "storage_backend": "postgresql" if settings.database_url.get_secret_value() else "sqlite",
                     "llm_budget": 6, "tool_budget": 12, "retrieval_rounds": 2,
                     "answer_schema_version":2,"operational_policy_version":1}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()+b"".join(p.read_bytes() for p in files)).hexdigest()


def presentation_fingerprint():
    base=Path('frontend/src')
    if not (base/'App.tsx').exists():return None
    paths=sorted(p for p in base.rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css'} and '.test.' not in p.name)
    identity={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


async def evaluate(settings, store, provider, split="smoke", release_id=None, limit=None, concurrency=1, case_ids=None, modes=("agentic",)):
    """Scope diagnostic hooks to one suite; preserve real capacity across suites."""
    generate=provider.generate
    client=getattr(provider,'client',None)
    hooks=client.event_hooks.setdefault('response',[]) if client else None
    previous_hooks=list(hooks) if hooks is not None else []
    try:
        return await _evaluate(settings,store,provider,split,release_id,limit,concurrency,case_ids,modes)
    finally:
        provider.generate=generate
        if hooks is not None:hooks[:]=previous_hooks


async def _evaluate(settings, store, provider, split="smoke", release_id=None, limit=None, concurrency=1, case_ids=None, modes=("agentic",)):
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
    validate_suite_corpus(settings.data_dir,split,cases,store,release)
    configuration = configuration_fingerprint(settings)
    run_id = f"{release['id']}-{provider.settings.generation_model.replace('/', '_')}-{split}-{fingerprint[:8]}-{configuration[:8]}-c{concurrency}"
    run_id += '-agentic'
    records_path = settings.reports_dir / "runs" / run_id / "records.json"
    metadata_path = records_path.with_name("metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"as_of": str(local_date()), "configuration_sha256": configuration, "suite_sha256": fingerprint, "split": split, "storage_backend": "postgresql" if store.postgres else "sqlite"}
    presentation=presentation_fingerprint()
    if metadata_path.exists() and metadata.get('presentation_sha256')!=presentation:
        raise ValueError('Presentation changed; use a new evaluation output directory')
    metadata['presentation_sha256']=presentation
    json_write(metadata_path, metadata)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    attempts_path=records_path.parent/'attempts'
    for record in records:
        preserve_attempt(attempts_path,record,'imported_latest_checkpoint')
    agent = Agent(store, provider)
    case_label=contextvars.ContextVar('evaluation_case',default=None)
    generate=provider.generate
    generated_cases = set()
    generation_contexts = {}
    async def capture_structured_output(schema,instruction,payload,budget):
        result=await generate(schema,instruction,payload,budget)
        label=case_label.get()
        if label and schema.__name__ == 'Draft':
            generated_cases.add(label)
            generation_contexts[label]=[item for item in payload.get('evidence',[]) if isinstance(item,dict)]
        if label and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',label):
            output=result.model_dump(mode='json')
            checksum=hashlib.sha256(json.dumps(output,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            json_write(records_path.parent/'model_outputs'/f'{label}-{budget.llm_calls}-{checksum[:16]}.json',
                {'scope':'Unverified structured model output for developer diagnosis; never delivered as a chatbot answer. No hidden reasoning.',
                 'schema':schema.__name__,'case_mode':label,'llm_calls':budget.llm_calls,'output':output})
        return result
    provider.generate=capture_structured_output
    provider_ready_at=time.monotonic()+await asyncio.to_thread(store.cooldown)
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
            try:provider_ready_at=max(provider_ready_at,time.monotonic()+float(response.headers.get('retry-after','0')))
            except ValueError:pass
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
        if remaining<min(7000,capacity*.85):
            provider_ready_at=max(provider_ready_at,time.monotonic()+seconds)
            # The closure disappears when a suite returns. Persist the actual
            # header-derived wait in this isolated operator DB so the next
            # suite/process cannot accidentally start with a depleted bucket.
            await asyncio.to_thread(store.set_cooldown,math.ceil(seconds))
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
        label_token=case_label.set(f"{case['id']}-{mode}")
        try:
            result = await agent.run(ChatRequest(session_id=session_id,message=case['question'],
                project='ring4' if case.get('project')=='ring4' else None,history=case.get('history',[]),as_of=case.get('as_of') or metadata['as_of'],mode=mode),emit,release['id'])
        finally:case_label.reset(label_token)
        return {'case_id':case['id'],'mode':mode,
                'answer_origin': 'llm' if f"{case['id']}-{mode}" in generated_cases else 'deterministic',
                'evaluation_context':generation_contexts.get(f'{case["id"]}-{mode}',[]),
                'result':result.model_dump(mode='json')}
    for start in range(0,len(pending),concurrency):
        cooldown=provider_ready_at-time.monotonic()
        if cooldown>60:
            print(json.dumps({'evaluation_deferred_provider_retry_after':round(cooldown,2)}),flush=True)
            break
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
        # Keep transient/budget failures in the denominator and continue the
        # remaining locked cases; never rerun the failed case in this pass.
        # Long provider cooldown is handled before starting the next case.
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
    if split not in {'smoke', 'supplemental', 'natural'}:
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,79}',split):
            raise ValueError('Invalid frozen suite name')
        registry_path=data_dir/'evaluation'/'registry.json'
        registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
        entry=registry.get('suites',{}).get(split)
        if not entry or entry.get('executable') is not True:
            raise ValueError('Suite is draft or has not been reviewed and frozen for execution')
        if type(entry.get('cases')) is not int or not 1<=entry['cases']<=1000:
            raise ValueError('Frozen suite needs a bounded positive case count')
        base=(data_dir/'evaluation').resolve()
        path=(base/entry['path']).resolve()
        freeze_path=(base/entry['freeze_path']).resolve()
        if not path.is_relative_to(base) or not freeze_path.is_relative_to(base):
            raise ValueError('Frozen suite path outside evaluation directory')
        freeze=json.loads(freeze_path.read_text())
        fingerprint=hashlib.sha256(path.read_bytes()).hexdigest()
        cases=dataset(path)
        if (freeze.get('status')!='frozen' or freeze.get('annotation_status')!='reviewed'
                or freeze.get('suite_sha256')!=fingerprint or freeze.get('cases')!=entry['cases']
                or len(cases)!=entry['cases'] or not freeze.get('corpus_id')
                or not freeze.get('review_method') or not freeze.get('reviewed_by_role')):
            raise ValueError('Frozen suite annotation or identity is incomplete')
        for case in cases:
            if (case.get('split')!=split or case.get('review_status')!='reviewed'
                    or not case.get('rubric') or not case.get('as_of')
                    or not isinstance(case.get('question'),str) or not 1<=len(case['question'])<=4000
                    or case.get('answerability') not in {'answerable','needs_user_fact','missing_source','out_of_scope','interaction_only'}):
                raise ValueError('Frozen case contract is incomplete')
            date.fromisoformat(case['as_of'])
            if case['answerability']=='answerable' and (not case.get('gold_chunk_ids')
                    or not case.get('required_propositions') or not case.get('required_evidence_groups')
                    or case.get('legal_review_status')!='reviewed'):
                raise ValueError('Answerable case needs reviewed legal propositions and evidence')
            if case['answerability']=='answerable':
                validate_evidence_annotation(case)
        return cases,fingerprint
    path = data_dir / 'evaluation' / f'{split}.jsonl'
    freeze_path = path.with_name('freeze.json') if split == 'smoke' else path.with_suffix('.freeze.json')
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = json.loads(freeze_path.read_text())
    cases = dataset(path)
    expected = {'smoke':20,'supplemental':4,'natural':8}[split]
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


def validate_evidence_annotation(case):
    def strings(values):
        return isinstance(values,list) and 1<=len(values)<=64 and all(isinstance(v,str) and v.strip() for v in values)
    if not strings(case['gold_chunk_ids']) or not strings(case['required_propositions']):
        raise ValueError('Gold and propositions must be nonempty bounded string lists')
    groups=case['required_evidence_groups']
    if not isinstance(groups,list) or not 1<=len(groups)<=16:
        raise ValueError('Evidence groups must be a bounded list')
    ids=[]
    for group in groups:
        if not isinstance(group,dict) or not isinstance(group.get('id'),str) or not group['id'].strip():
            raise ValueError('Evidence group needs an ID')
        alternatives=group.get('alternatives')
        if not isinstance(alternatives,list) or not 1<=len(alternatives)<=16 or not all(strings(a) for a in alternatives):
            raise ValueError('Evidence group needs alternatives of required chunk IDs')
        ids.append(group['id'])
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate evidence group IDs')


def evidence_group_coverage(chunk_ids,groups):
    selected=set(chunk_ids)
    matched=[g['id'] for g in groups if any(set(alternative)<=selected for alternative in g['alternatives'])]
    return {'required_groups':len(groups),'matched_groups':len(matched),
            'complete':bool(groups) and len(matched)==len(groups)}


def citizen_metrics(rows, cases):
    """Separate task denominators fixed before execution; absent cases remain visible."""
    expected={case['id']:case for case in cases if case.get('answerability')}
    if not expected:return None
    observed={row['id']:row for row in rows}
    groups={}
    for answerability in ('answerable','needs_user_fact','missing_source','out_of_scope','interaction_only'):
        ids=[key for key,case in expected.items() if case['answerability']==answerability]
        counts={name:0 for name in ('pass','partial','fail','awaiting_review','not_run')}
        false_abstention=0
        for key in ids:
            row=observed.get(key)
            verdict=row.get('review','awaiting_review') if row else 'not_run'
            if verdict not in counts:verdict='awaiting_review'
            if answerability=='answerable' and verdict=='pass' and row.get('status')!='answered':verdict='fail'
            counts[verdict]+=1
            false_abstention+=bool(row and answerability=='answerable' and row.get('status') in {'clarification_needed','insufficient_evidence'})
        groups[answerability]={'expected':len(ids),'counts':counts,'false_abstention':false_abstention}
    eligible=[case for case in cases if case.get('answerability')=='answerable' and case.get('required_evidence_groups')]
    citation_coverage=[]
    for case in eligible:
        row=observed.get(case['id'])
        if row:
            citation_coverage.append(evidence_group_coverage(
                [c['id'] for c in row.get('answer',{}).get('citations',[])],case['required_evidence_groups']))
    return {'groups':groups,'citation_evidence_coverage':{'eligible_cases':len(eligible),
            'executed_cases':len(citation_coverage),'complete_cases':sum(c['complete'] for c in citation_coverage)},
            'scope':'Fixed task groups; evidence-group presence does not prove entailment, legal accuracy or user comprehension.'}


def validate_suite_corpus(data_dir,split,cases,store,release):
    if split in {'smoke','supplemental','natural'}:return
    registry=json.loads((data_dir/'evaluation/registry.json').read_text())
    binding=json.loads((data_dir/'evaluation'/registry['suites'][split]['freeze_path']).read_text())
    if binding['corpus_id']!=release['id']:
        raise ValueError('Frozen suite corpus mismatch')
    chunks={r['id'] for r in store.rows('SELECT id FROM chunks WHERE release_id=?',(release['id'],))}
    required={cid for case in cases for group in case.get('required_evidence_groups',[])
              for alternative in group['alternatives'] for cid in alternative}
    if required-chunks or any(set(case.get('gold_chunk_ids',[]))-chunks for case in cases):
        raise ValueError('Frozen gold missing from selected corpus')


async def evaluate_retrieval(settings, store, provider, split='smoke'):
    """Read-only hybrid retrieval evaluation; no generation or session writes."""
    cases, fingerprint = frozen_dataset(settings.data_dir, split)
    release = await asyncio.to_thread(store.release, None, True)
    if not release:
        raise ValueError('No corpus release to evaluate')
    validate_suite_corpus(settings.data_dir,split,cases,store,release)
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
        recall=len(set(ids)&set(case['gold_chunk_ids']))/len(set(case['gold_chunk_ids']))
        rows.append({'id': case['id'], 'has_history': bool(case.get('history')), 'gold_chunk_ids': case['gold_chunk_ids'], 'retrieved_chunk_ids': ids,
                     'hit': bool(set(ids) & set(case['gold_chunk_ids'])), 'gold_recall_at_8':recall,
                     'elapsed_ms': round((time.monotonic() - started) * 1000)})
        if case.get('required_evidence_groups'):
            rows[-1]['evidence_group_coverage']=evidence_group_coverage(ids,case['required_evidence_groups'])
    report = {'checked_at': utcnow().isoformat(), 'split': split, 'suite_sha256': fingerprint,
              'release': release['id'], 'configuration_sha256': configuration_fingerprint(settings),
              'backend': 'postgresql' if store.postgres else 'sqlite', 'k': 8,
              'eligible_cases': len(rows), 'hits': sum(r['hit'] for r in rows),
              'hit_rate': sum(r['hit'] for r in rows) / len(rows) if rows else None,
              'gold_recall_at_8':statistics.mean(r['gold_recall_at_8'] for r in rows) if rows else None,
              'history_groups':{str(h):{'cases':len(g:=[r for r in rows if r['has_history']==h]),'gold_recall_at_8':statistics.mean(r['gold_recall_at_8'] for r in g) if g else None} for h in [False,True]},
              'generation_calls': 0, 'results': rows,
              'scope': 'Raw-question hybrid search including bounded source-replacement candidates; no history rewriting or agent tool calls. Any gold chunk in top 8 counts as a hit. Not legal answer accuracy.'}
    grouped=[row for row in rows if 'evidence_group_coverage' in row]
    if grouped:
        report['complete_evidence_coverage']={'eligible_cases':len(grouped),
            'complete_cases':sum(row['evidence_group_coverage']['complete'] for row in grouped)}
    json_write(settings.reports_dir / 'retrieval' / f'{split}.json', report)
    return report
