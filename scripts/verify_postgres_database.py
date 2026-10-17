"""Restore into a newly created disposable database; never touches the serving database."""
import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.security import new_token,utcnow


def main():
    env=dotenv_values('.env');owner=env['ADMIN_DATABASE_URL'];runtime=env['DATABASE_URL']
    name='landlaw_restore_'+uuid.uuid4().hex[:12]
    a=b=None;created=False
    with psycopg.connect(owner,autocommit=True,connect_timeout=15) as control:
        serving=control.execute('select current_database()').fetchone()[0]
        assert serving!=name and name.startswith('landlaw_restore_')
        try:
            control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));created=True
            isolated_owner=make_conninfo(owner,dbname=name)
            isolated_runtime=make_conninfo(runtime,dbname=name)
            with psycopg.connect(isolated_owner,autocommit=True,connect_timeout=15) as c:
                assert c.execute('select current_database()').fetchone()[0]==name
                for path in sorted(Path('migrations').glob('*.sql')):c.execute(path.read_text())
            settings=Settings().model_copy(update={'database_url':SecretStr(isolated_owner),'admin_database_url':SecretStr('')})
            a=Store(settings);a.restore(Path('data/backups/ring4-public-corpus.json'))
            release=a.release(None,True)
            assert len(release['documents'])==59 and all(d.get('project') in {None,'ring4'} for d in release['documents'])
            b=Store(settings.model_copy(update={'database_url':SecretStr(isolated_runtime)}))
            sid=str(uuid.uuid4());token=new_token();b.create_session(sid,token)
            assert b.authenticate(sid,token) and not b.authenticate(sid,'wrong')
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes=list(pool.map(lambda _:b.start_turn(str(uuid.uuid4()),sid,'fixture'),range(2)))
            assert outcomes.count(None)==outcomes.count('session_busy')==1
            assert not b.rows("SELECT has_table_privilege(current_user,'public.messages','INSERT') AS allowed")[0]['allowed']
            assert not a.rows('select * from messages') and not a.rows('select * from traces') and not a.rows('select * from answer_cache')
            assert a.rows('SELECT count(*) AS n FROM chunks')[0]['n']==7555
            result={'passed':True,'checked_at':utcnow().isoformat(),'corpus_id':release['id'],'documents':59,'chunks':7555,
                    'isolated_database':True,'runtime_role_tested':True,'parallel_session_lease':True,'history_writes_revoked':True,
                    'scope':'A newly created disposable PostgreSQL database on the existing instance; serving database never migrated or changed.'}
            Path('reports/postgres-restore-database.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        finally:
            if a:a.close()
            if b:b.close()
            if created:
                # Only the unpredictable name created by this invocation can be removed.
                control.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'passed':False,'error_type':type(error).__name__}))
        raise SystemExit(1) from None
