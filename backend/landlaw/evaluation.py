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
from .security import new_token, utcnow


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
        critical_failed, reviewed, valid = [], 0, 0
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
                if case.get("critical") and not review.get("passed"):
                    critical_failed.append(case["id"])
        p95 = sorted(latencies)[math.ceil(len(latencies)*.95)-1] if latencies else None
        summary["results"].append({"mode": mode, "completed": len(items), "reviewed": reviewed,
            "recall_at_8": statistics.mean(recalls) if recalls else None,
            "answer_pass_rate": statistics.mean(scores) if scores else None,
            "citation_id_valid_rate": valid/len(items) if items else None,
            "claim_support_rate": statistics.mean(support) if support else None,
            "p95_seconds": p95, "llm_calls": sum(r["result"]["llm_calls"] for r in items),
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


async def evaluate(settings, store, provider, split="dev", release_id=None, limit=None):
    path = settings.data_dir / "evaluation/questions.jsonl"
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    cases = [c for c in dataset(path) if c["split"] == split]
    if not provider.configured:
        raise ValueError("Cannot evaluate without real GEMINI_API_KEY")
    release = store.release(release_id)
    if not release:
        raise ValueError("No corpus release to evaluate")
    run_id = f"{release['id']}-{provider.settings.gemini_model}-{split}-{fingerprint[:8]}"
    records_path = settings.reports_dir / "runs" / run_id / "records.json"
    records = json.loads(records_path.read_text()) if records_path.exists() else []
    agent, executed = Agent(store, provider), 0
    async def emit(_):
        pass
    for case in cases:
        for mode in ("baseline", "agentic"):
            if any(r["case_id"] == case["id"] and r["mode"] == mode and r["result"]["status"] not in {"limited", "error"} for r in records):
                continue
            if limit is not None and executed >= limit:
                break
            session_id = str(uuid.uuid4())
            await asyncio.to_thread(store.create_session, session_id, new_token())
            request = ChatRequest(session_id=session_id, message=case["question"], project=case.get("project"),
                                  as_of=case.get("as_of"), mode=mode)
            result = await agent.run(request, emit, release["id"])
            records = [r for r in records if not (r["case_id"] == case["id"] and r["mode"] == mode)]
            records.append({"case_id": case["id"], "mode": mode, "result": result.model_dump(mode="json")})
            json_write(records_path, records)
            executed += 1
            if result.status == "limited":
                break
            await asyncio.sleep(1)
        if (limit is not None and executed >= limit) or (records and records[-1]["result"]["status"] == "limited"):
            break
    review_path = settings.data_dir / "evaluation/reviews.json"
    report = summarise(records, cases, fingerprint, json.loads(review_path.read_text()) if review_path.exists() else {})
    report.update({"run_id": run_id, "release": release["id"], "model": provider.settings.gemini_model,
                   "embedding_model": provider.settings.embedding_model, "split": split})
    json_write(settings.reports_dir / "latest.json", report)
    from html import escape
    html = "<!doctype html><html lang='vi'><meta charset='utf-8'><title>Benchmark</title>"
    html += "<style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px}pre{white-space:pre-wrap}</style>"
    html += "<h1>Báo cáo benchmark</h1><p>Kết quả chưa rà soát chưa chứng nhận chất lượng pháp lý.</p><pre>" + escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>"
    (settings.reports_dir / "benchmark.html").write_text(html, encoding="utf-8")
    return report
