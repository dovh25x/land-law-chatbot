"""Verify the frozen 120-case benchmark and optionally its exact corpus passages."""
import argparse
import json
from pathlib import Path

from landlaw.evaluation import validate_frozen_benchmark


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path)
    args = parser.parse_args()
    store = None
    release_id = None
    if args.release:
        release = json.loads(args.release.read_text())
        class FileCorpus:
            def __init__(self):
                from landlaw.models import Document, Chunk
                self.documents = {d['id']: Document.model_validate(d) for d in release['documents']}
                self.chunks = {c['id']: Chunk.model_validate(c) for d in release['documents'] for c in d['chunks']}
            def chunk(self, cid, _): return self.chunks.get(cid)
            def document(self, did, _): return self.documents.get(did)
        store, release_id = FileCorpus(), release['id']
    root = Path('data/evaluation')
    result = validate_frozen_benchmark(root/'questions.jsonl', root/'acceptance-freeze.json',
        root/'gold-sources.json', store, release_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
