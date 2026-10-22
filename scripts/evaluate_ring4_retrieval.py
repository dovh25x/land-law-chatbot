"""Offline Recall@5 retrieval evaluation for Ring Road 4 gold cases.

No Groq request and no production write: restores a versioned backup into a
temporary SQLite file, imports the pinned receipts, activates the v2 standing
policy, and measures raw and admitted retrieval. ``--baseline`` disables the
reviewed-evidence ranking branch to quantify the retrieval fix.
"""
import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from landlaw.config import Settings
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.provider import GroqProvider
from landlaw.source_policy import applicability
from landlaw.store import Store

SPLITS = ('smoke', 'supplemental', 'natural')


async def evaluate(settings, store, provider, release, as_of_map, split):
    rows = [json.loads(line) for line in (Path('data/evaluation') / f'{split}.jsonl').read_text().splitlines() if line.strip()]
    cases = []
    for row in rows:
        gold = list(row.get('gold_chunk_ids') or [])
        if not gold:
            cases.append({'id': row['id'], 'skipped': 'no_gold_chunk_ids'})
            continue
        as_of = date.fromisoformat(row['as_of'])
        vector = await provider.embed(row['question'], query=True, release=release)
        hits = await asyncio.to_thread(store.search, row['question'], vector, row.get('project'),
                                       release['id'], settings.embedding_model, as_of)
        reviews = await asyncio.to_thread(store.scoped_source_reviews, release,
            [(item.document.id, item.chunk.id, item.chunk.checksum) for item in hits], as_of)
        admitted = []
        for item in hits:
            status = reviews.get(f"{item.document.id}:{item.chunk.id}")
            state = applicability(item.document, as_of, item.chunk)
            if status in {'fresh', 'standing', 'reviewed_window'} and state in {'current', 'provision_specific', 'context'}:
                admitted.append(item)
        top5 = hits[:5]
        admitted_top5 = admitted[:5]
        gold_set = set(gold)
        record = {
            'id': row['id'], 'split': split, 'as_of': row['as_of'],
            'gold_chunk_ids': gold,
            'top5': [item.chunk.id for item in top5],
            'admitted_top5': [item.chunk.id for item in admitted_top5],
            'recall_at_5': len(gold_set & {item.chunk.id for item in top5}) / len(gold_set),
            'hit_at_5': bool(gold_set & {item.chunk.id for item in top5}),
            'admitted_recall_at_5': len(gold_set & {item.chunk.id for item in admitted_top5}) / len(gold_set),
            'admitted_hit_at_5': bool(gold_set & {item.chunk.id for item in admitted_top5}),
            'admitted_total': len(admitted),
        }
        groups = row.get('required_evidence_groups') or []
        if groups:
            available = {item.chunk.id for item in admitted_top5}
            record['complete_evidence_at_5'] = all(set(group) & available for group in groups)
        cases.append(record)
    scored = [case for case in cases if 'recall_at_5' in case]
    return {
        'split': split, 'scored_cases': len(scored), 'total_cases': len(cases),
        'recall_at_5': sum(case['recall_at_5'] for case in scored) / max(1, len(scored)),
        'hit_at_5': sum(bool(case['hit_at_5']) for case in scored) / max(1, len(scored)),
        'admitted_recall_at_5': sum(case['admitted_recall_at_5'] for case in scored) / max(1, len(scored)),
        'admitted_hit_at_5': sum(bool(case['admitted_hit_at_5']) for case in scored) / max(1, len(scored)),
        'cases': cases,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', default='data/staging/phase2c-current/acceptance-context-pack-backup.json')
    parser.add_argument('--receipts', default='reports/source-review-20261022/receipts-20261022')
    parser.add_argument('--policy-v1', default='reports/source-review-20261022/source-gate-20261022.json')
    parser.add_argument('--policy', default='reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json')
    parser.add_argument('--sqlite', default='/tmp/opencode/phase-a/retrieval-eval.db')
    parser.add_argument('--output', default='reports/qa/ring4-retrieval-offline-current.json')
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()

    settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
                        groq_api_key='', sqlite_path=args.sqlite, allow_stale_generation=False,
                        local_embedding_model_dir=Path('models/e5'))
    store = Store(settings)
    if args.baseline:
        store.admissible_chunk_scope = lambda release, as_of: {}
    store.restore(Path(args.backup))
    release = store.release(None, True)
    for path in sorted(Path(args.receipts).glob('*.json')):
        record_source_review(store, path)
    activate_source_gate(store, Path(args.policy_v1))
    activate_source_gate(store, Path(args.policy))
    provider = GroqProvider(settings, store)
    splits = {split: await evaluate(settings, store, provider, release, {}, split) for split in SPLITS}
    store.close()
    report = {
        'mode': 'baseline' if args.baseline else 'current',
        'release_id': release['id'],
        'embedding_model': settings.embedding_model,
        'splits': splits,
        'summary': {
            'scored_cases': sum(split['scored_cases'] for split in splits.values()),
            'recall_at_5': sum(split['recall_at_5'] * split['scored_cases'] for split in splits.values()) / max(1, sum(split['scored_cases'] for split in splits.values())),
            'admitted_recall_at_5': sum(split['admitted_recall_at_5'] * split['scored_cases'] for split in splits.values()) / max(1, sum(split['scored_cases'] for split in splits.values())),
        },
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
