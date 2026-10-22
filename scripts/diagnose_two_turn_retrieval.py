"""Reproduce the two-turn planning/resettlement conversation offline.

Read-only for the repo and production: restores a versioned backup into a
temporary SQLite file, imports only the pinned receipts, activates the v2
standing policy and prints candidate/admission states per turn. No Groq call.
"""
import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from landlaw.config import Settings
from landlaw.conversation import contextual_retrieval_query
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.provider import GroqProvider
from landlaw.source_policy import applicability
from landlaw.store import Store

TURNS = [
    ("turn1", "Tôi có được bố trí chỗ ở mới nếu nhà hiện tại đang ở diện quy hoạch không?", None),
    ("turn2", "đất tôi ở thuộc dự án Vành đai 4", [
        {"role": "user", "content": "Tôi có được bố trí chỗ ở mới nếu nhà hiện tại đang ở diện quy hoạch không?"},
        {"role": "assistant", "content": "Câu trả lời trước đó."},
    ]),
    ("turn3-follow-up", "vậy nếu chưa có sổ đỏ?", [
        {"role": "user", "content": "đất tôi ở thuộc dự án Vành đai 4"},
        {"role": "assistant", "content": "Câu trả lời trước đó."},
    ]),
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', default='data/staging/phase2c-current/acceptance-context-pack-backup.json')
    parser.add_argument('--receipts', default='reports/source-review-20261022/receipts-20261022')
    parser.add_argument('--policy-v1', default='reports/source-review-20261022/source-gate-20261022.json')
    parser.add_argument('--policy', default='reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json')
    parser.add_argument('--sqlite', default='/tmp/opencode/phase-a/two-turn-diagnosis.db')
    parser.add_argument('--output', default='reports/qa/phase-a-two-turn-diagnosis.json')
    parser.add_argument('--as-of', default='2026-10-22')
    args = parser.parse_args()

    settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
                        groq_api_key='', sqlite_path=args.sqlite, allow_stale_generation=False,
                        local_embedding_model_dir=Path('models/e5'))
    store = Store(settings)
    store.restore(Path(args.backup))
    release = store.release(None, True)
    for path in sorted(Path(args.receipts).glob('*.json')):
        record_source_review(store, path)
    activate_source_gate(store, Path(args.policy_v1))
    activate_source_gate(store, Path(args.policy))
    provider = GroqProvider(settings, store)
    as_of = date.fromisoformat(args.as_of)
    report = {
        'release_id': release['id'],
        'as_of': args.as_of,
        'policy_sha256': store.source_review_metadata(release)['policy_sha256'],
        'turns': [],
    }
    for label, message, history in TURNS:
        query, inherited = contextual_retrieval_query(message, history or [])
        vector = await provider.embed(query, query=True, release=release)
        hits = await asyncio.to_thread(store.search, query, vector, 'ring4', release['id'],
                                       settings.embedding_model, as_of)
        reviews = await asyncio.to_thread(store.scoped_source_reviews, release,
            [(item.document.id, item.chunk.id, item.chunk.checksum) for item in hits], as_of)
        candidates = []
        admitted = []
        for item in hits:
            key = f"{item.document.id}:{item.chunk.id}"
            gate = reviews.get(key)
            state = applicability(item.document, as_of, item.chunk)
            keep = gate in {'fresh', 'standing', 'reviewed_window'} and state in {'current', 'provision_specific', 'context'}
            candidates.append({
                'chunk_id': item.chunk.id, 'document_id': item.document.id,
                'locator': item.chunk.locator, 'score': round(item.score, 6),
                'gate': gate, 'applicability': state, 'admitted': keep,
                'excerpt': ' '.join(item.chunk.text.split())[:160],
            })
            if keep:
                admitted.append(item)
        report['turns'].append({
            'label': label, 'message': message,
            'retrieval_query': query, 'inherited': inherited,
            'candidates': candidates,
            'admitted_chunk_ids': [item.chunk.id for item in admitted],
            'admitted_count': len(admitted),
        })
    store.close()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({item['label']: item['admitted_count'] for item in report['turns']}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
