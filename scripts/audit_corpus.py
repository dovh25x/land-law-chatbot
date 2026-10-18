"""Audit an immutable corpus snapshot and reproduce parsing without publishing.

This checks reproducibility and software integrity, not legal certification.
It never embeds, calls generation, updates source reviews, or writes a database.
"""
import argparse
import asyncio
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from landlaw.cli import reviewed_source_files
from landlaw.config import Settings
from landlaw.evaluation import frozen_dataset
from landlaw.ingest import Quarantine, collect_source, coverage
from landlaw.models import Document, Relation
from landlaw.publication import validate_corpus
from landlaw.security import digest, official_url, utcnow


async def audit(snapshot, output, replay):
    if output.exists():
        raise ValueError('Output exists; preserve the prior audit and select a new output path')
    release = json.loads(snapshot.read_text())
    snapshot_docs = {doc['id']: doc for doc in release['documents']}
    sources = json.loads(Path('data/sources.json').read_text())
    manifest = {s['id']: s for s in sources}
    settings = Settings(_env_file=None)
    errors, warnings, documents = [], [], []
    chunks, seen_doc_checksums = {}, defaultdict(list)
    chunk_checksums = defaultdict(list)
    norms, raw_files = [], {}
    now = utcnow()
    try:
        validate_corpus(release)
        publication_validation = True
    except ValueError as exc:
        publication_validation = False
        errors.append({'kind': 'publication_validation', 'detail': str(exc)})
    for doc in release['documents']:
        ident = doc['id']
        try:
            Document.model_validate(doc)
        except ValueError:
            errors.append({'kind': 'document_schema', 'document_id': ident})
        seen_doc_checksums[doc['checksum']].append(ident)
        source = manifest.get(ident)
        if source is None:
            errors.append({'kind': 'missing_manifest', 'document_id': ident})
            source = {}
        if source.get('review_status') != 'verified':
            errors.append({'kind': 'unreviewed_active_source', 'document_id': ident})
        if doc.get('project') not in (None, 'ring4'):
            errors.append({'kind': 'out_of_scope', 'document_id': ident})
        checked = datetime.fromisoformat(doc['checked_at'])
        stamp = min(checked, datetime.fromisoformat(release['checked_at']))
        findings = {'id': ident, 'chunks': len(doc['chunks']), 'kind': doc['source_kind'],
                    'project': doc.get('project'), 'snapshot_age_days': (now-stamp).total_seconds()/86400,
                    'snapshot_fresh_without_receipts': stamp >= now-timedelta(days=7),
                    'source_review_notes': doc.get('source_review_notes', ''),
                    'source_file_count': len(doc.get('source_files', []))}
        for key in ('title', 'url', 'document_number', 'effective_from', 'effective_to', 'provision_validity'):
            if doc.get(key) != source.get(key, [] if key == 'provision_validity' else None):
                errors.append({'kind': 'manifest_metadata_mismatch', 'document_id': ident, 'field': key})
        raw = []
        for name, expected in reviewed_source_files(source):
            path = Path(name)
            if not path.resolve().is_relative_to(Path('data/raw').resolve()):
                errors.append({'kind': 'raw_path_outside_data_raw', 'document_id': ident})
                continue
            if name not in raw_files:
                actual = digest(path.read_bytes()) if path.exists() else None
                raw_files[name] = {'path': name, 'expected_sha256': expected, 'actual_sha256': actual,
                                   'matches': bool(expected and expected == actual)}
            if not raw_files[name]['matches']:
                errors.append({'kind': 'raw_provenance_mismatch', 'document_id': ident, 'path': name})
        for name in source.get('raw_paths', []):
            if Path(name).exists():
                raw.append(Path(name).read_bytes())
        if not raw or hashlib.sha256(b''.join(raw)).hexdigest() != doc['checksum']:
            errors.append({'kind': 'document_checksum_mismatch', 'document_id': ident})
        for attachment in doc.get('source_files', []):
            if not official_url(attachment['url'], doc.get('publication_url') or doc['url']):
                errors.append({'kind': 'nonofficial_attachment', 'document_id': ident})
        short, encoding = [], []
        for chunk in doc['chunks']:
            cid = chunk['id']
            if cid in chunks:
                errors.append({'kind': 'duplicate_chunk_id', 'chunk_id': cid})
            chunks[cid] = chunk
            if chunk['document_id'] != ident or digest(chunk['text']) != chunk['checksum']:
                errors.append({'kind': 'chunk_integrity', 'chunk_id': cid})
            if chunk.get('embedding_model') != release['embedding_model']:
                errors.append({'kind': 'chunk_embedding_model', 'chunk_id': cid})
            vector = chunk.get('embedding') or []
            if len(vector) == 384 and all(type(v) in (int,float) and math.isfinite(v) for v in vector):
                norm = math.sqrt(sum(v*v for v in vector))
                norms.append(norm)
                if abs(norm-1) > 1e-4:
                    errors.append({'kind': 'embedding_norm', 'chunk_id': cid})
            if not chunk.get('id', '').endswith('-parent'):
                chunk_checksums[chunk['checksum']].append(cid)
            if len(chunk['text'].strip()) < 60:
                short.append(cid)
            if '\ufffd' in chunk['text']:
                encoding.append({'id': cid, 'replacement_chars': chunk['text'].count('\ufffd')})
            if chunk.get('page'):
                prefix = ident+'-'
                part = cid[len(prefix):].split('-',1)[0] if cid.startswith(prefix) else ''
                mapped = [a for a in doc.get('source_files', []) if part.isdigit()
                          and a['first_page_index'] <= int(part) <= a['last_page_index']]
                if len(mapped) != 1:
                    warnings.append({'kind': 'physical_page_without_exact_attachment', 'chunk_id': cid})
        findings.update({'short_chunks': short, 'encoding_candidates': encoding})
        documents.append(findings)
    for chunk in chunks.values():
        parent = chunk.get('parent_id')
        if parent and (parent not in chunks or chunks[parent]['document_id'] != chunk['document_id']):
            errors.append({'kind': 'parent_reference', 'chunk_id': chunk['id']})
    ids = {d['id'] for d in release['documents']}
    for relation in release['relations']:
        Relation.model_validate(relation)
        if relation['source_id'] not in ids or relation['target_id'] not in ids:
            errors.append({'kind': 'resolved_relation_missing_endpoint', 'relation': relation})
    suites = {}
    for split in ('smoke', 'supplemental', 'natural'):
        cases, fingerprint = frozen_dataset(Path('data'), split)
        missing = [{'case_id': c['id'], 'chunk_id': cid} for c in cases for cid in c.get('gold_chunk_ids', []) if cid not in chunks]
        suites[split] = {'cases': len(cases), 'sha256': fingerprint, 'missing_gold_chunks': missing}
        errors.extend({'kind': 'missing_gold', **m} for m in missing)
    if replay:
        async with httpx.AsyncClient() as client:
            for finding in documents:
                ident = finding['id']
                try:
                    parsed = await collect_source(manifest[ident], settings, client, offline=True, allow_ocr=False)
                    old = {c['id']: c['checksum'] for c in snapshot_docs[ident]['chunks']}
                    new = {c.id: c.checksum for c in parsed.chunks}
                    finding['parser_replay'] = {'matches': old == new,
                        'original_chunks': len(old), 'reproduced_chunks': len(new),
                        'removed_ids': sorted(old.keys()-new.keys()), 'added_ids': sorted(new.keys()-old.keys()),
                        'changed_ids': sorted(k for k in old.keys() & new.keys() if old[k] != new[k])}
                    if old != new:
                        errors.append({'kind': 'parser_replay_mismatch', 'document_id': ident})
                except (OSError, ValueError, httpx.HTTPError, Quarantine) as exc:
                    finding['parser_replay'] = {'matches': False, 'error_type': type(exc).__name__}
                    errors.append({'kind': 'parser_replay_error', 'document_id': ident, 'error_type': type(exc).__name__})
                print(json.dumps({'audit_progress':ident, 'parser_matches':finding['parser_replay']['matches']}), flush=True)
    source_commit = await asyncio.to_thread(subprocess.check_output, ['git','rev-parse','HEAD'],text=True)
    report = {'checked_at': now.isoformat(),
        'source_commit': source_commit.strip(),
        'snapshot_path': str(snapshot), 'snapshot_sha256': digest(snapshot.read_bytes()),
        'manifest_sha256': digest(Path('data/sources.json').read_bytes()),
        'corpus_id': release['id'], 'publication_validation': publication_validation,
        'documents': len(documents), 'chunks': len(chunks), 'by_source_kind': dict(Counter(d['kind'] for d in documents)),
        'snapshot_stale_documents_without_receipts': sum(not d['snapshot_fresh_without_receipts'] for d in documents),
        'raw_artifacts': list(raw_files.values()), 'embedding_norm_min': min(norms), 'embedding_norm_max': max(norms),
        'duplicate_document_bodies': [v for v in seen_doc_checksums.values() if len(v)>1],
        'duplicate_nonparent_chunk_groups': [v for v in chunk_checksums.values() if len(v)>1],
        'coverage_gaps': release.get('coverage_gaps', []), 'unresolved_relations': release.get('unresolved_relations', []),
        'legacy_ingest_coverage': coverage(release), 'suite_integrity': suites,
        'errors': errors, 'warnings': warnings, 'document_findings': documents,
        'scope': 'Offline artifact integrity and parser reproducibility only. No embedding regeneration, no database writes, no generation; checksums and heuristic flags are not independent legal review.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(output),'documents':len(documents),'chunks':len(chunks),'errors':len(errors),'warnings':len(warnings)},ensure_ascii=False))
    return bool(errors)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay-parser',action='store_true')
    args=parser.parse_args()
    raise SystemExit(int(asyncio.run(audit(args.snapshot,args.output,args.replay_parser))))
