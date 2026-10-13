"""Restore the real encrypted backup into a disposable local PostgreSQL database.

Backup reads the source and runs its normal expired-session cleanup. All restore, rollback and restart
operations are restricted to a loopback PostgreSQL service, never Supabase.
"""
import json
import math
import os
import tempfile
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from pydantic import SecretStr

from landlaw.config import Settings
from landlaw.models import ChatResult
from landlaw.security import digest, local_date, new_token, utcnow
from landlaw.store import Store


def main():
    settings=Settings().for_operator()
    recovery=os.environ.get('RECOVERY_DATABASE_URL','')
    info=conninfo_to_dict(recovery)
    if info.get('host') not in {'127.0.0.1','localhost'} or not settings.backup_encryption_key.get_secret_value():
        raise SystemExit('An isolated loopback PostgreSQL service and backup encryption key are required')
    name='landlaw_restore_'+uuid.uuid4().hex[:12]
    target_url=make_conninfo(recovery,dbname=name)
    target_settings=settings.model_copy(update={'app_env':'development','database_url':SecretStr(target_url),
        'admin_database_url':SecretStr('')})
    source,target=Store(settings),None
    checks={}
    try:
        with psycopg.connect(recovery,autocommit=True) as admin:
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        with psycopg.connect(target_url) as conn:
            for role in ('anon','authenticated'):
                if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
            for path in sorted(Path('migrations').glob('[0-9][0-9][0-9]_*.sql')):
                conn.execute(path.read_text())
        with tempfile.TemporaryDirectory(prefix='landlaw-postgres-restore-') as temporary:
            backup=Path(temporary)/'private.enc'
            source.backup(backup,include_sessions=True)
            checks['encrypted_backup']=not backup.read_bytes().startswith(b'{')
            target=Store(target_settings)
            target.restore(backup)
            original_ids={r['id'] for r in source.rows('SELECT id FROM releases')}
            checks['all_releases_restored']=original_ids=={r['id'] for r in target.rows('SELECT id FROM releases')}
            checks['chunks_restored']=source.rows('SELECT count(*) AS n FROM chunks')[0]['n']==target.rows('SELECT count(*) AS n FROM chunks')[0]['n']
            checks['immutable_archive_bytes']=all(source.release(r)==target.release(r) for r in original_ids)
            checks['release_pointer']=source.state('active_release')==target.state('active_release')
            checks['publication_evidence']=source.rows("SELECT * FROM app_state WHERE key LIKE 'publication:%' ORDER BY key")==target.rows("SELECT * FROM app_state WHERE key LIKE 'publication:%' ORDER BY key")
            dimensions={r['n'] for r in target.rows('SELECT DISTINCT vector_dims(embedding) AS n FROM chunks WHERE embedding IS NOT NULL')}
            checks['restored_embedding_dimensions']=dimensions=={r['n'] for r in source.rows('SELECT DISTINCT vector_dims(embedding) AS n FROM chunks WHERE embedding IS NOT NULL')}
            # Retiring obsolete staging can leave only the active provider's dimension
            # in the real backup. Exercise the absent dimension in this disposable
            # database with an explicitly synthetic storage fixture, never Supabase.
            for dimension in {384,768,1024}-dimensions:
                fixture_id=f'isolated-technical-vector-{dimension}'
                fixture={'id':fixture_id,'documents':[{'id':fixture_id,'title':'Isolated technical vector fixture; no legal evidence',
                    'url':'https://example.com/isolated-fixture','source_kind':'official_news','checked_at':utcnow().isoformat(),
                    'checksum':digest(fixture_id),'chunks':[{'id':fixture_id,'document_id':fixture_id,
                    'text':'Isolated technical vector fixture; no legal evidence','locator':'technical fixture','checksum':digest(fixture_id),
                    'embedding_model':fixture_id,'embedding':[1/math.sqrt(dimension)]*dimension}]}]}
                target.stage(fixture)
            for dimension in (384,768,1024):
                row=target.rows('SELECT release_id,id,embedding_model FROM chunks WHERE vector_dims(embedding)=? LIMIT 1',(dimension,))[0]
                chunk=target.chunk(row['id'],row['release_id'])
                hits=target.search(chunk.text[:250],chunk.embedding,release_id=row['release_id'],embedding_model=row['embedding_model'])
                checks[f'hybrid_{dimension}']=bool(hits) and all(e.chunk.embedding_model==row['embedding_model'] for e in hits)
            session_id,token=str(uuid.uuid4()),new_token()
            target.create_session(session_id,token)
            answer=ChatResult(status='insufficient_evidence',content='Isolated recovery exercise',as_of=local_date(),
                trace_id=str(uuid.uuid4()),model=settings.generation_model,embedding_model=settings.embedding_model,mode='baseline')
            target.save_turn(session_id,'Isolated recovery exercise',answer)
            releases=[r for r in target.rows('SELECT id FROM releases ORDER BY created_at') if r['id'] in original_ids]
            target.publish(releases[-1]['id']); target.publish(releases[0]['id'])
            checks['rollback']=target.state('active_release')==releases[0]['id'] and target.state('previous_release')==releases[-1]['id']
            target.unpublish()
            checks['first_release_withdrawal']=target.state('active_release') is None and len(target.messages(session_id))==2
            target.publish(releases[-1]['id']); target.close(); target=Store(target_settings)
            checks['restart']=target.state('active_release')==releases[-1]['id'] and target.authenticate(session_id,token) and target.trace(answer.trace_id,session_id) is not None
            report={'passed':all(checks.values()),'checked_at':utcnow().isoformat(),'checks':checks,
                'backup_sha256':digest(backup.read_bytes()),'release':releases[-1]['id'],'releases':len(original_ids),
                'scope':'Full real encrypted source backup restored into a disposable separate PostgreSQL database on a loopback service. Absent embedding dimensions exercised with clearly labelled synthetic technical fixtures only in that disposable database. Production pointer unchanged.'}
        Path('reports/postgres-restore.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        if not report['passed']: raise SystemExit(1)
    finally:
        source.close()
        if target: target.close()
        with psycopg.connect(recovery,autocommit=True) as admin:
            admin.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))


if __name__=='__main__': main()
