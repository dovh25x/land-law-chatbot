"""Recompute release gates from bound evidence, without changing serving state."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, dataset
from landlaw.ingest import coverage
from landlaw.ops import record_source_review
from landlaw.publication import validate_corpus
from landlaw.security import utcnow
from landlaw.store import Store
from pydantic import SecretStr


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def model_gate(report, candidate, suite, settings):
    """Technical rubric gate, never an independent legal certification."""
    cases = dataset(Path('data/evaluation')/(suite+'.jsonl'))
    rows = report.get('results', [])
    expected = {case['id']: case for case in cases}
    sources = {chunk['id']: (doc, chunk) for doc in candidate['documents'] for chunk in doc['chunks']}
    if (report.get('storage_backend') != 'postgresql'
            or report.get('identity') != {'release': candidate['id'],
                'configuration_sha256': configuration_fingerprint(settings)}
            or report.get('suite_sha256') != checksum(Path('data/evaluation')/(suite+'.jsonl'))
            or len(rows) != len(cases) or {r['id'] for r in rows} != set(expected)):
        return False
    for row in rows:
        case = expected[row['id']]
        answer = row.get('answer', {})
        answer_hash = hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        if (row.get('question') != case['question'] or row.get('rubric') != case['rubric']
                or row.get('as_of') != case.get('as_of')
                or row.get('gold_chunk_ids') != case.get('gold_chunk_ids', [])
                or row.get('answer_sha256') != answer_hash
                or answer.get('corpus_release') != candidate['id']
                or answer.get('model') != settings.generation_model
                or row.get('status') != answer.get('status')
                or row.get('status') in {'limited', 'error'}
                or row.get('citations_valid') is False
                or row.get('review') not in {'pass', 'partial', 'fail'}
                or not row.get('review_note') or not row.get('review_method')):
            return False
        citations = {citation['id']: citation for citation in answer.get('citations', [])}
        if answer.get('status') == 'answered' and (not citations or not answer.get('verified_claims')):
            return False
        for identifier, citation in citations.items():
            pair = sources.get(identifier)
            if (not pair or citation.get('document_id') != pair[0]['id']
                    or citation.get('url') != pair[0]['url']
                    or citation.get('locator') != pair[1]['locator']
                    or citation.get('excerpt') != pair[1]['text']):
                return False
        if any(not claim.get('citation_ids') or set(claim['citation_ids'])-citations.keys()
               for claim in answer.get('verified_claims', [])):
            return False
    if suite != 'natural':
        return all(row['review'] == 'pass' for row in rows)
    substantive = [row for row in rows if expected[row['id']].get('gold_chunk_ids')]
    safety = [row for row in rows if not expected[row['id']].get('gold_chunk_ids')]
    return (len(substantive) == 6 and sum(row['review'] == 'pass' and row['status'] == 'answered'
            for row in substantive) >= 5
            and all(row['review'] == 'pass' for row in safety))


def inspect(manifest):
    inputs = manifest['inputs']
    # Every artifact is bound to exact bytes before it is interpreted.
    for item in inputs.values():
        if item is not None and checksum(item['path']) != item['sha256']:
            raise ValueError('Evidence checksum mismatch')
    candidate = json.loads(Path(inputs['snapshot']['path']).read_text())
    validate_corpus(candidate)
    settings = Settings()
    postgres = settings.model_copy(update={'database_url': SecretStr('postgresql://isolated-evaluation')})
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    checks = {'tested_revision': manifest.get('source_commit') == head,
              'coverage': coverage(candidate)['publication_ready']}
    with tempfile.TemporaryDirectory(prefix='landlaw-readiness-') as folder:
        local = settings.model_copy(update={'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
                                           'sqlite_path': str(Path(folder)/'readiness.db')})
        store = Store(local)
        try:
            store.restore(Path(inputs['backup']['path']))
            restored = store.release()
            checks['backup_matches_candidate'] = (restored['id'] == candidate['id']
                and restored['documents'] == candidate['documents'] and restored['relations'] == candidate['relations'])
            for key, item in inputs.items():
                if key.startswith('source_receipt:') and item:
                    record_source_review(store, Path(item['path']))
            checks['source_freshness'] = store.source_fresh(restored)
        finally:
            store.close()
    for suite in ('smoke', 'supplemental', 'natural'):
        item = inputs.get('review:'+suite)
        checks['generation:'+suite] = bool(item) and model_gate(
            json.loads(Path(item['path']).read_text()), candidate, suite, postgres)
    canonical_hash = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
    backup_hash = inputs['backup']['sha256']
    thresholds = {'smoke': 9/11, 'supplemental': 1, 'natural': .75}
    for backend in ('sqlite', 'postgresql'):
        item = inputs.get('restore:'+backend)
        result = json.loads(Path(item['path']).read_text()) if item else {}
        measured = {r['split']: r for r in result.get('retrieval', [])}
        checks['restore:'+backend] = (result.get('restored_exactly') is True
            and result.get('corpus_id') == candidate['id'] and result.get('snapshot_sha256') == canonical_hash
            and result.get('backup_sha256') == backup_hash
            and all(measured.get(s, {}).get('backend') == backend
                and measured[s].get('gold_recall_at_8', -1) >= threshold for s, threshold in thresholds.items()))
    item = inputs.get('software')
    software = json.loads(Path(item['path']).read_text()) if item else {}
    required = {'backend', 'secrets', 'frontend_unit', 'frontend_build', 'frontend_e2e'}
    entries = {r['name']: r for r in software.get('checks', [])}
    checks['software'] = (software.get('source_commit') == head and required <= entries.keys()
        and all(entries[name].get('exit_code') == 0
            and checksum(entries[name]['log']) == entries[name]['log_sha256'] for name in required))
    item = inputs.get('release_download')
    download = json.loads(Path(item['path']).read_text()) if item else {}
    checks['release_download'] = (download.get('downloaded') is True
        and download.get('corpus_id') == candidate['id'] and download.get('backup_sha256') == backup_hash
        and str(download.get('url', '')).startswith('https://github.com/')
        and bool(download.get('path')) and checksum(download['path']) == backup_hash)
    item = inputs.get('postgres_runtime')
    runtime = json.loads(Path(item['path']).read_text()) if item else {}
    checks['postgres_runtime'] = (runtime.get('passed') is True and runtime.get('corpus_id') == candidate['id']
        and all(runtime.get(key) is True for key in ('runtime_role_tested', 'parallel_session_lease', 'history_writes_revoked')))
    return {'checked_at': utcnow().isoformat(), 'source_commit': head, 'corpus_id': candidate['id'],
            'ready': all(checks.values()), 'checks': checks,
            'blocked': [name for name, passed in checks.items() if not passed],
            'scope': 'Recomputed technical publication gates; not independent legal certification or deployment proof.',
            'manifest': manifest, 'serving_state_changed': False}


def require_ready(path):
    recorded = json.loads(Path(path).read_text())
    checked = datetime.fromisoformat(recorded['checked_at'])
    if checked.tzinfo is None or not utcnow()-timedelta(days=1) <= checked <= utcnow():
        raise ValueError('Release readiness evidence expired or has no timezone')
    result = inspect(recorded['manifest'])
    if not result['ready']:
        raise ValueError('Publication gates failed: '+', '.join(result['blocked']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite a historical readiness report')
    result = inspect(json.loads(args.manifest.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('ready', 'corpus_id', 'blocked')}))
    raise SystemExit(0 if result['ready'] else 1)
