import asyncio
import hashlib
import json
import math
import statistics
import uuid
from pathlib import Path

from .agent import Agent
from .ingest import json_write
from .models import ChatRequest
from .security import local_date, new_token, utcnow


def dataset(path: Path):
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({q["id"] for q in cases}) != len(cases):
        raise ValueError("Duplicate benchmark IDs")
    return cases


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
    files = [Path(__file__).with_name(name) for name in ("agent.py", "provider.py", "embedding.py", "store.py", "config.py", "publication.py", "models.py", "security.py", "api.py")]
    configuration = {"model": settings.generation_model, "llm_provider": settings.llm_provider, "embedding_model": settings.embedding_model,
                     "dimensions": settings.embedding_dimensions, 'embedding_provider':settings.embedding_provider,
                     "timeout_seconds": settings.turn_timeout_seconds,
                     "llm_budget": 6, "tool_budget": 12, "retrieval_rounds": 2}
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()+b"".join(p.read_bytes() for p in files)).hexdigest()


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
    configuration = configuration_fingerprint(settings)
    run_id = f"{release['id']}-{provider.settings.generation_model.replace('/', '_')}-{split}-{fingerprint[:8]}-{configuration[:8]}-c{concurrency}"
    records_path = settings.reports_dir / "runs" / run_id / "records.json"
    metadata_path = records_path.with_name("metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {"as_of": str(local_date()), "configuration_sha256": configuration}
    json_write(metadata_path, metadata)
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    agent, executed = Agent(store, provider), 0
    async def emit(_):
        pass
    pending = [(case,mode) for case in cases for mode in ('baseline','agentic')
        if not any(r['case_id']==case['id'] and r['mode']==mode and r['result']['status'] not in {'limited','error'} for r in records)]
    if limit is not None:
        pending=pending[:limit]
    async def execute(case,mode):
        session_id = str(uuid.uuid4())
        await asyncio.to_thread(store.create_session,session_id,new_token())
        # Persist preceding turns only in this private benchmark session.
        for turn in case.get('history',[]):
            preceding = await agent.run(ChatRequest(session_id=session_id,message=turn,
                project=case.get('project'),as_of=case.get('as_of') or metadata['as_of'],mode=mode),emit,release['id'])
            await asyncio.to_thread(store.save_turn,session_id,turn,preceding)
        result = await agent.run(ChatRequest(session_id=session_id,message=case['question'],
            project=case.get('project'),as_of=case.get('as_of') or metadata['as_of'],mode=mode),emit,release['id'])
        return {'case_id':case['id'],'mode':mode,'result':result.model_dump(mode='json')}
    for start in range(0,len(pending),concurrency):
        results=await asyncio.gather(*(execute(c,m) for c,m in pending[start:start+concurrency]))
        for result in results:
            records=[r for r in records if not (r['case_id']==result['case_id'] and r['mode']==result['mode'])]
            records.append(result)
            json_write(records_path,records)
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
    report['acceptance_passed'] = bool(report['acceptance_passed'] and split=='acceptance'
        and len(cases)==80 and all(c.get('ground_truth_status')=='source_checked' for c in cases)
        and all(r['reviewed']==80 and r['source_review_complete'] for r in report['results']))
    report['latency_scope'] = f'Paired CLI run, concurrency {concurrency}; public API single-user p95 measured separately.'
    for name in ('source-audit','runtime-tests'):
        evidence_path = settings.reports_dir/f'{name}.json'
        evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
        field = name.replace('-','_')
        report[field+'_passed'] = bool(evidence.get('passed') and evidence.get('release')==release['id']
            and (name=='source-audit' or evidence.get('configuration_sha256')==configuration))
        report[field+'_sha256'] = hashlib.sha256(evidence_path.read_bytes()).hexdigest() if evidence_path.exists() else None
    json_write(settings.reports_dir / ('smoke.json' if split=='smoke' else 'latest.json'), report)
    from html import escape
    html = "<!doctype html><html lang='vi'><meta charset='utf-8'><title>Benchmark</title>"
    html += "<style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px}pre{white-space:pre-wrap}</style>"
    html += "<h1>Báo cáo benchmark</h1><p>Kết quả chưa rà soát chưa chứng nhận chất lượng pháp lý.</p><pre>" + escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>"
    (settings.reports_dir / ('smoke.html' if split=='smoke' else 'benchmark.html')).write_text(html, encoding="utf-8")
    return report
