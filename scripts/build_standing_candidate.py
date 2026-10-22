"""Build a read-only v2 standing-snapshot candidate from a corpus backup.

The production database is never opened. Receipt files are imported by their
existing canonical bytes, not re-reviewed: their SHA256 must already match the
pinned v1 policy and every passage checksum must exist in the active release.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from pydantic import SecretStr

from landlaw.config import Settings
from landlaw.ops import activate_source_gate, build_standing_policy
from landlaw.store import Store


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def sha256(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True,
                        help='Corpus-only backup containing the active release')
    parser.add_argument('--policy-v1', type=Path, required=True,
                        help='Currently active v1 scoped policy')
    parser.add_argument('--receipts', type=Path, required=True,
                        help='Directory of canonical pinned receipt JSON files')
    parser.add_argument('--output', type=Path, required=True,
                        help='Path for the v2 candidate JSON')
    parser.add_argument('--evidence', type=Path, required=True,
                        help='Path for non-secret build/verification evidence')
    parser.add_argument('--expected-current', type=int, default=43)
    parser.add_argument('--expected-reviewed', type=int, default=74)
    parser.add_argument('--expected-standing', type=int, default=42)
    args = parser.parse_args()

    backup_bytes = args.backup.read_bytes()
    policy_v1 = json.loads(args.policy_v1.read_text())
    v1_hash = sha256(canonical(policy_v1))
    receipt_paths = sorted(args.receipts.glob('*.json'))
    if not receipt_paths:
        raise SystemExit('No receipt files found')

    with tempfile.TemporaryDirectory(prefix='landlaw-standing-candidate-') as folder:
        settings = Settings(_env_file=None, sqlite_path=str(Path(folder) / 'candidate.db'))
        settings = settings.model_copy(update={
            'database_url': SecretStr(''), 'admin_database_url': SecretStr('')})
        store = Store(settings)
        try:
            store.restore(args.backup)
            release = store.release(None, True)
            if not release:
                raise SystemExit('Backup has no active release')
            if policy_v1.get('version') != 1 or policy_v1.get('release_id') != release['id']:
                raise SystemExit('Policy v1 does not match the backup release')
            documents = {doc['id']: doc for doc in release.get('documents', [])}
            imported = {}
            for path in receipt_paths:
                receipt = json.loads(path.read_text())
                doc = documents.get(receipt.get('document_id'))
                encoded = canonical(receipt)
                ident = sha256(encoded)
                if not doc or doc.get('checksum') != receipt.get('checksum'):
                    raise SystemExit(f'Receipt document/checksum mismatch: {path.name}')
                if policy_v1.get('receipts', {}).get(doc['id']) != ident:
                    raise SystemExit(f'Receipt is not the exact pinned v1 bytes: {path.name}')
                if receipt.get('status') != 'unchanged':
                    raise SystemExit(f'Adverse receipt cannot be migrated: {path.name}')
                if not receipt.get('checked_at') or not receipt.get('verified_scope'):
                    raise SystemExit(f'Receipt lacks pinned review scope: {path.name}')
                for scope in receipt['verified_scope']:
                    for chunk_id, checksum in (scope.get('chunk_checksums') or {}).items():
                        chunk = store.chunk(chunk_id, release['id'])
                        if not chunk or chunk.document_id != doc['id'] or chunk.checksum != checksum:
                            raise SystemExit(f'Receipt passage mismatch: {path.name}')
                with store.transaction() as conn:
                    store.execute(conn, 'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?) '
                                  'ON CONFLICT(id) DO NOTHING',
                                  (ident, release['id'], doc['id'], doc['checksum'],
                                   receipt['checked_at'], receipt['status'], encoded))
                imported[doc['id']] = ident

            if set(imported) != set(policy_v1.get('receipts', {})):
                raise SystemExit('Receipt cohort does not exactly match policy v1')
            activate_source_gate(store, args.policy_v1)
            active = store.source_gate(release['id'])
            if active.get('version') != 1 or sha256(canonical(active)) != v1_hash:
                raise SystemExit('Policy v1 did not activate with the pinned hash')

            first = build_standing_policy(store, active)
            second = build_standing_policy(store, active)
            if first != second:
                raise SystemExit('Standing policy build is not deterministic')
            if first['supersedes'] != {'version': 1, 'policy_sha256': v1_hash}:
                raise SystemExit('Standing policy supersedes the wrong v1 hash')
            reviewed = sum(len(entry['chunks']) for entry in first['standing'].values())
            standing = sum(len(entry['standing_chunks']) for entry in first['standing'].values())
            windows = sum(len(entry['legal_windows']) for entry in first['standing'].values())
            if (reviewed, standing) != (args.expected_reviewed, args.expected_standing):
                raise SystemExit(f'Unexpected reviewed/standing counts: {reviewed}/{standing}')
            for doc_id, entry in first['standing'].items():
                covered = set(entry['standing_chunks'])
                for scope in entry['legal_windows']:
                    covered |= set(scope['chunk_checksums'])
                if covered != set(entry['chunks']):
                    raise SystemExit(f'Standing policy loses or invents passages: {doc_id}')

            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(first, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
            activate_source_gate(store, args.output)
            checked = {}
            eligible_ids = {}
            for day in ('2026-10-22', '2026-10-23', '2026-10-25', '2026-10-28',
                        '2026-11-01', '2025-01-01'):
                status = store.source_gate_status(store.release(None, True), date.fromisoformat(day))
                checked[day] = {key: status.get(key) for key in
                                ('mode', 'eligible_passages', 'usable', 'operational_expiry',
                                 'reviewed_at', 'reviewed_as_of', 'whole_corpus_verified')}
            current = store.source_gate_status(store.release(None, True), date(2026, 10, 22))
            if current['eligible_passages'] != args.expected_current or not current['usable']:
                raise SystemExit(f'Current-day count changed: {current["eligible_passages"]}')
            # qd-10 is historical after 2026-04-02 and must not appear in current scope.
            current_ids = set(first['standing']['qd-10-2026-hanoi']['chunks']) if (
                'qd-10-2026-hanoi' in first['standing']) else set()
            if current_ids and store.scoped_source_reviews(
                    release, [('qd-10-2026-hanoi', chunk_id, checksum)
                              for chunk_id, checksum in first['standing']['qd-10-2026-hanoi']['chunks'].items()],
                    date(2026, 10, 22)).get('qd-10-2026-hanoi:' + next(iter(current_ids))) == 'standing':
                raise SystemExit('Historical document was admitted as current standing evidence')

            # Reversible, explicit rollback: the v1 bytes are restored, not edited.
            store.set_state('source_gate:' + release['id'], canonical(policy_v1))
            rollback = store.source_gate_status(release, date(2026, 10, 22))
            if rollback.get('mode') != 'scoped_receipts':
                raise SystemExit('Rollback did not restore the v1 policy')

            evidence = {
                'status': 'CANDIDATE_READY_NOT_ACTIVATED',
                'release_id': release['id'],
                'source_commit': subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'backup_sha256': hashlib.sha256(backup_bytes).hexdigest(),
                'policy_v1_sha256': v1_hash,
                'policy_v2_sha256': sha256(canonical(first)),
                'receipt_files': {path.name: sha256(path.read_bytes()) for path in receipt_paths},
                'reviewed_passages': reviewed,
                'standing_passages': standing,
                'legal_windows': windows,
                'documents_with_standing_chunks': sorted(
                    doc_id for doc_id, entry in first['standing'].items() if entry['standing_chunks']),
                'current_day_eligible_passages': current['eligible_passages'],
                'checks': checked,
                'rollback_policy_v1_mode': rollback.get('mode'),
                'production_database_opened': False,
                'database_write_scope': 'temporary SQLite only',
                'external_llm_requests': 0,
                'scope_note': ('Migrates exactly the pinned receipt bytes and passage checksums. '
                               'Long legal windows are preserved; only <=2-day rotation windows '
                               'become standing chunks. This does not certify legal currency.'),
            }
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'passed': True, 'policy_v2_sha256': evidence['policy_v2_sha256'],
                              'current_day_eligible_passages': current['eligible_passages'],
                              'reviewed_passages': reviewed, 'standing_passages': standing,
                              'output': str(args.output)}, ensure_ascii=False))
        finally:
            store.close()


if __name__ == '__main__':
    main()
