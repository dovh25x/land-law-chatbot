"""Rebuild offline staging, reusing exact vectors; never activate or refresh reviews."""
import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from landlaw.config import Settings
from landlaw.embedding import contract
from landlaw.ingest import build_corpus
from landlaw.provider import GroqProvider
from landlaw.publication import validate_corpus
from landlaw.security import digest
from landlaw.store import Store
from pydantic import SecretStr


async def prepare(source, output):
    output.mkdir(parents=True, exist_ok=False)
    original = json.loads(source.read_text())
    settings = Settings().model_copy(update={'database_url': SecretStr(''),
        'admin_database_url': SecretStr(''), 'reports_dir': output})
    validate_corpus(original)
    contract(settings, original)
    old = {(d['title'], c['checksum']): c['embedding']
           for d in original['documents'] for c in d['chunks']}
    # Seeding is not inference. Refuse conflicting checkpoints rather than
    # replacing either historical input or already cached vector silently.
    checkpoints = settings.data_dir / 'checkpoints'
    checkpoints.mkdir(parents=True, exist_ok=True)
    for (title, checksum), vector in old.items():
        key = digest(f'embedding-format-v1:{settings.embedding_model}:{title}:{checksum}')
        path = checkpoints / f'{key}.json'
        if path.exists():
            if json.loads(path.read_text())['embedding'] != vector:
                raise ValueError('Existing checkpoint differs from snapshot vector')
        else:
            path.write_text(json.dumps({'embedding': vector}))
    with tempfile.TemporaryDirectory(prefix='landlaw-prepare-') as folder:
        store = Store(settings.model_copy(update={'sqlite_path': str(Path(folder)/'staging.db')}))
        provider = GroqProvider(settings, store)
        try:
            candidate, coverage = await build_corpus(settings, provider, offline=True, embed=True)
            validate_corpus(candidate)
            reused = changed = 0
            for doc in candidate['documents']:
                for chunk in doc['chunks']:
                    previous = old.get((doc['title'], chunk['checksum']))
                    if previous is None:
                        changed += 1
                    else:
                        if chunk['embedding'] != previous:
                            raise ValueError('Unchanged passage vector changed')
                        reused += 1
            store.stage(candidate)
            # Local activation is needed to export a corpus-only restore file.
            # This database is disposable; no serving database is opened.
            store.publish(candidate['id'])
            store.backup(output/'candidate-backup.json')
            (output/'candidate.json').write_text(json.dumps(candidate, ensure_ascii=False))
            result = {'corpus_id': candidate['id'], 'source_corpus_id': original['id'],
                'source_sha256': digest(source.read_bytes()), 'candidate_sha256': digest((output/'candidate.json').read_bytes()),
                'documents': len(candidate['documents']), 'chunks': reused+changed,
                'unchanged_vectors_preserved_exactly': reused, 'new_or_changed_chunks': changed,
                'coverage': coverage, 'activated_on_serving_database': False,
                'freshness_review_performed': False, 'publication_approved': False}
            (output/'preparation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps({key: value for key, value in result.items() if key != 'coverage'}))
        finally:
            await provider.close()
            store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(prepare(args.source, args.output))
