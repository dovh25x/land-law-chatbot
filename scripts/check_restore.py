"""Rehearse recovery against disposable local databases using the actual staged corpus."""
import json
import tempfile
import uuid
from pathlib import Path

from pydantic import SecretStr

from landlaw.config import Settings
from landlaw.models import ChatResult
from landlaw.security import local_date, new_token, utcnow
from landlaw.store import Store


def main():
    settings = Settings().model_copy(update={'database_url': SecretStr(''), 'admin_database_url': SecretStr('')})
    files = sorted((settings.data_dir/'staging').glob('*.json'), key=lambda p:p.stat().st_mtime)
    if len(files) < 2 or not settings.backup_encryption_key.get_secret_value():
        raise SystemExit('Two real staging releases and an offline backup encryption key required')
    checks = {}
    with tempfile.TemporaryDirectory(prefix='landlaw-restore-') as temporary:
        folder = Path(temporary)
        original = Store(settings.model_copy(update={'sqlite_path': str(folder/'original.db')}))
        restored = Store(settings.model_copy(update={'sqlite_path': str(folder/'restored.db')}))
        try:
            for path in (files[0], files[-1]):
                payload = json.loads(path.read_text())
                original.stage(payload)
                # Private recovery exercise only; never changes the public Postgres pointer.
                original.publish(payload['id'])
            expected = original.state('active_release')
            previous = original.state('previous_release')
            sid, token = str(uuid.uuid4()), new_token()
            original.create_session(sid, token)
            answer = ChatResult(status='insufficient_evidence', content='Technical recovery exercise', as_of=local_date(),
                trace_id=str(uuid.uuid4()), model=settings.gemini_model, embedding_model=settings.embedding_model, mode='baseline')
            original.save_turn(sid, 'Technical recovery exercise', answer)
            backup = folder/'private.enc'
            original.backup(backup, include_sessions=True)
            checks['encrypted_archive'] = not backup.read_bytes().startswith(b'{') and token.encode() not in backup.read_bytes()
            restored.restore(backup)
            checks['corpus_pointer'] = restored.state('active_release') == expected
            checks['source_checksums'] = {d.id:d.checksum for d in original.documents()} == {d.id:d.checksum for d in restored.documents()}
            checks['chunk_count'] = original.rows('SELECT count(*) AS n FROM chunks')[0]['n'] == restored.rows('SELECT count(*) AS n FROM chunks')[0]['n']
            checks['history_and_trace'] = len(restored.messages(sid)) == 2 and restored.trace(answer.trace_id,sid) is not None
            checks['session_isolation'] = restored.authenticate(sid,token) and not restored.authenticate(sid,'wrong-token')
            restored.publish(previous)
            checks['rollback'] = restored.state('active_release') == previous and restored.state('previous_release') == expected
            restored.publish(expected)
            checks['forward_restore'] = restored.state('active_release') == expected
            report = {'checked_at':utcnow().isoformat(), 'passed':all(checks.values()), 'checks':checks,
                      'release':expected, 'scope':'disposable SQLite databases with real staged corpus; public corpus unchanged'}
        finally:
            original.close(); restored.close()
    Path('reports/restore-rehearsal.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
