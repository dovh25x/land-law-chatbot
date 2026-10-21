"""Raw-query Recall@5, frozen 20+4+8 labels, excluding S06 by user instruction."""
import asyncio
import hashlib
import json
import statistics
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, frozen_dataset
from landlaw.local_embedding import Encoder, MODEL
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.store import Store

OUT = Path(__file__).parent
CORPUS = Path('data/staging/phase2c-current/release-v5.json')
BASE = Path('reports/phase2c-current-20261021')


async def run():
    for name, expected in [('model_quantized.onnx', MODEL['onnx_sha256']),
                           ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
        assert Encoder.file_sha(Path('models/e5') / name) == expected
    encoder = Encoder(Path('models/e5'))
    corpus = json.loads(CORPUS.read_text())
    chunks = {c['id'] for d in corpus['documents'] for c in d['chunks']}
    suite_hashes, cases, excluded = {}, [], []
    for split in ('smoke', 'supplemental', 'natural'):
        rows, suite_hashes[split] = frozen_dataset(Path('data'), split)
        for case in rows:
            gold = set(case.get('gold_chunk_ids', []))
            if case['id'] == 'S06':
                excluded.append({'id': case['id'], 'reason': 'Excluded before execution by explicit user instruction'})
            elif not gold:
                excluded.append({'id': case['id'], 'reason': 'No positive gold chunk labels; not a recall denominator'})
            else:
                assert not gold - chunks, 'Frozen gold missing from candidate'
                cases.append((split, case, gold))
    with tempfile.TemporaryDirectory(prefix='landlaw-phase3b-retrieval-') as folder:
        settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
            groq_api_key='', allow_stale_generation=False, sqlite_path=str(Path(folder) / 'test.db'))
        store = Store(settings)
        try:
            store.stage(corpus)
            store.publish(corpus['id'])
            for p in sorted((BASE / 'receipts-final').glob('*.json')):
                record_source_review(store, p)
            activate_source_gate(store, BASE / 'source-gate-final.json')
            release = store.release(None, True)
            rows = []
            for split, case, gold in cases:
                start = time.monotonic()
                vector = await asyncio.to_thread(encoder.encode, case['question'], True)
                as_of = date.fromisoformat(case['as_of'])
                hits = await asyncio.to_thread(store.search, case['question'], vector, case.get('project'),
                    release['id'], settings.embedding_model, as_of)
                ids = [h.chunk.id for h in hits[:5]]
                reviews = store.scoped_source_reviews(release,
                    [(h.document.id, h.chunk.id, h.chunk.checksum) for h in hits[:5]], as_of)
                admitted = [h.chunk.id for h in hits[:5]
                            if reviews.get(h.document.id + ':' + h.chunk.id) == 'fresh']
                rows.append({'id': case['id'], 'split': split, 'as_of': case['as_of'],
                    'gold_chunk_ids': sorted(gold), 'top5_chunk_ids': ids,
                    'gold_hits': len(gold & set(ids)), 'gold_count': len(gold),
                    'recall_at_5': len(gold & set(ids)) / len(gold),
                    'review_admitted_top5_chunk_ids': admitted,
                    'review_admitted_recall_at_5': len(gold & set(admitted)) / len(gold),
                    'source_review_states': reviews, 'elapsed_ms': round((time.monotonic() - start) * 1000)})
                print(json.dumps({k: rows[-1][k] for k in ('id', 'recall_at_5', 'review_admitted_recall_at_5')}) , flush=True)
            report = {'storage_backend': 'isolated_sqlite', 'corpus_id': corpus['id'],
                'corpus_sha256': hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
                'runtime_fingerprint': configuration_fingerprint(settings),
                'suite_sha256': suite_hashes, 'eligible_cases': len(rows),
                'gold_label_denominator': sum(r['gold_count'] for r in rows),
                'gold_hits_at_5': sum(r['gold_hits'] for r in rows),
                'macro_recall_at_5': statistics.mean(r['recall_at_5'] for r in rows),
                'micro_recall_at_5': sum(r['gold_hits'] for r in rows) / sum(r['gold_count'] for r in rows),
                'review_admitted_macro_recall_at_5': statistics.mean(r['review_admitted_recall_at_5'] for r in rows),
                'by_split': {split: {'cases': len(group := [r for r in rows if r['split'] == split]),
                    'macro_recall_at_5': statistics.mean(r['recall_at_5'] for r in group)}
                    for split in ('smoke', 'supplemental', 'natural')},
                'excluded_cases': excluded, 'rows': rows, 'external_llm_requests': 0,
                'scope': 'Raw-question E5/hybrid search including existing replacement candidates. '
                    'No question rewriting, generation, judge or agent tool expansion. Exact frozen chunk-ID '
                    'recall; related parent/child IDs do not count as the labelled chunk. Reviewed admission '
                    'is a separate diagnostic over the same original top5, without refilling. Dates are each '
                    'case date; this is not current-law answer accuracy or PostgreSQL performance.'}
            (OUT / 'retrieval-recall-at5.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        finally:
            store.close()


def forbidden(*args, **kwargs):
    raise AssertionError('No external HTTP in offline retrieval')


async def async_forbidden(*args, **kwargs):
    raise AssertionError('No external HTTP in offline retrieval')


with patch.object(httpx.Client, 'send', forbidden), patch.object(httpx.AsyncClient, 'send', async_forbidden):
    asyncio.run(run())
