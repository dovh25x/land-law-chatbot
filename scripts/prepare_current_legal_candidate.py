"""Add four source-bound provision excerpts; retain every existing chunk/vector.

Offline candidate preparation only. No database, HTTP, Groq, prompt or verifier
changes. Exact text slices come from the retained source snapshot, after review
against official signed documents. Existing releases are never overwritten.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import Relation
from landlaw.security import digest


def provision_excerpts(payload):
    docs = {d['id']: d for d in payload['documents']}
    chunks = {c['id']: c for d in docs.values() for c in d['chunks']}
    specs = [
        ('luat-dat-dai-2024', 'luat-dat-dai-2024-110-scope-4', 'Điều 111', 18,
         [('luat-dat-dai-2024-110-0-parent', '4. Hộ gia đình', '5. Hộ gia đình')]),
        ('nd-226-2025', 'nd-226-2025-15-scope-2-4', 'Điều 2', 16,
         [('nd-226-2025-15-0-parent', '4. Bổ sung điểm d', '5. Bổ sung khoản 5')]),
        ('nd-226-2025', 'nd-226-2025-34-scope-7-2a-5', 'Điều 7', 35,
         [('nd-226-2025-33-0-parent', '2. Thay thế, bãi bỏ các cụm từ, mẫu sau đây tại Nghị định số 88', '- Cụm từ “Mẫu quyết định'),
          ('nd-226-2025-34-0-parent', '- Cụm từ “xã, phường, thị trấn', '- Cụm từ “Ủy ban nhân dân cấp có thẩm quyền')]),
        ('nd-49-2026', 'nd-49-2026-23-scope-16-3g', 'Điều 16', 24,
         [('nd-49-2026-23-2-0', '3. Các quy định sau đây hết hiệu lực', None),
          ('nd-49-2026-24-0-parent', 'g) Các điều, khoản, điểm và Phụ lục của Nghị định số 226', None),
          ('nd-49-2026-25-0-0', 'g2) Phụ lục IV.', '4. Thay thế các cụm từ')]),
    ]
    excerpts, provenance = [], []
    for doc_id, ident, locator, page, parts in specs:
        if ident in chunks:
            raise ValueError('Candidate excerpt already exists; do not duplicate it')
        segments, offsets = [], []
        for source_id, start_text, end_text in parts:
            source = chunks[source_id]
            start = source['text'].index(start_text)
            end = source['text'].index(end_text, start) if end_text else len(source['text'])
            text = source['text'][start:end].strip()
            segments.append(text)
            offsets.append({'chunk_id': source_id, 'source_checksum': source['checksum'],
                            'page': source['page'], 'start': start, 'end': end,
                            'slice_sha256': digest(text)})
        text = '\n'.join(segments)
        excerpts.append({'id': ident, 'document_id': doc_id, 'text': text,
                         'locator': locator, 'page': page, 'parent_id': None,
                         'embedding_model': payload['embedding_model'], 'checksum': digest(text),
                         'embedding': None})
        provenance.append({'chunk_id': ident, 'document_id': doc_id,
                           'document_checksum': docs[doc_id]['checksum'], 'locator': locator,
                           'source_segments': offsets, 'text_sha256': digest(text),
                           'transformation': 'Exact source slices joined by newline; no added legal wording.'})
    return excerpts, provenance


def prepare(payload, encoder, relations=None):
    result = copy.deepcopy(payload)
    excerpts, provenance = provision_excerpts(payload)
    docs = {d['id']: d for d in result['documents']}
    if relations is not None:
        result['relations'] = [Relation.model_validate(r).model_dump(mode='json') for r in relations
                              if r['source_id'] in docs and r['target_id'] in docs]
    for chunk in excerpts:
        doc = docs[chunk['document_id']]
        chunk['embedding'] = encoder.encode(doc['title']+'\n'+chunk['text'], query=False)
        doc['chunks'].append(chunk)
    # Same identity algorithm/content inputs as the pinned ingest parser15.
    identity = {key: result[key] for key in ('documents', 'relations', 'unresolved_relations',
        'coverage_gaps', 'embedding_contract', 'place_aliases', 'embedding_model')}
    identity['parser_version'] = 15
    result['id'] = 'corpus-'+digest(json.dumps(identity, sort_keys=True, ensure_ascii=False))[:16]
    return result, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--relations', type=Path, default=Path('data/legal_relations.json'))
    args = parser.parse_args()
    if args.output.exists() or args.provenance.exists():
        raise ValueError('Use new output paths; immutable artifacts cannot be replaced')
    for name, checksum in [('model_quantized.onnx', MODEL['onnx_sha256']),
                           ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
        path = Path('models/e5')/name
        if not path.is_file() or Encoder.file_sha(path) != checksum:
            raise ValueError('Pinned local embedding files required; downloads are disabled')
    before = Encoder.file_sha(args.source)
    payload, provenance = prepare(json.loads(args.source.read_text()), Encoder(Path('models/e5')),
                                  json.loads(args.relations.read_text()))
    assert Encoder.file_sha(args.source) == before
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    args.provenance.write_text(json.dumps({'base_corpus_id': json.loads(args.source.read_text())['id'],
        'candidate_corpus_id': payload['id'], 'base_payload_sha256': before,
        'candidate_payload_sha256': Encoder.file_sha(args.output), 'existing_chunks_and_vectors_unchanged': True,
        'added_chunks': provenance, 'external_llm_requests': 0}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'corpus_id': payload['id'], 'added_chunks':len(provenance),
                      'payload_sha256': Encoder.file_sha(args.output)}))


if __name__ == '__main__':
    main()
