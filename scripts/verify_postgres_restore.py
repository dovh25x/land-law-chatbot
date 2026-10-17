"""Restore corpus into a disposable PostgreSQL schema, exercise runtime role, then remove only that schema."""
import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.security import new_token,utcnow
from pydantic import SecretStr


def scoped_store(settings,url,schema):
    result=Store(settings.model_copy(update={'database_url':SecretStr(url)}))
    result.pool.close()
    result.pool=ConnectionPool(url,min_size=0,max_size=4,kwargs={'autocommit':True,'prepare_threshold':None,
        'row_factory':psycopg.rows.dict_row,'options':f'-c search_path={schema},public -c statement_timeout=8000'})
    assert result.rows('SELECT current_schema() AS name')[0]['name']==schema
    return result


def main():
    env=dotenv_values('.env');owner=env.get('ADMIN_DATABASE_URL');runtime=env.get('DATABASE_URL')
    if not owner or not runtime:raise ValueError('Owner and runtime connections required')
    schema='landlaw_verify_'+uuid.uuid4().hex[:12]
    settings=Settings();a=b=None
    with psycopg.connect(owner,autocommit=True,connect_timeout=10) as connection:
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL('SET search_path TO {},public').format(sql.Identifier(schema)))
            for path in sorted(Path('migrations').glob('*.sql')):
                source=path.read_text()
                source='\n'.join(line for line in source.splitlines() if not line.startswith('CREATE EXTENSION'))
                source=source.replace('public.',schema+'.').replace('SCHEMA public','SCHEMA '+schema)
                source=source.replace('pg_catalog,public','pg_catalog,'+schema+',public').replace(schema+'.unaccent','public.unaccent')
                connection.execute(source)
            a=scoped_store(settings,owner,schema)
            a.restore(Path('data/backups/ring4-public-corpus.json'))
            release=a.release(None,True);assert len(release['documents'])==59
            b=scoped_store(settings,runtime,schema)
            sid=str(uuid.uuid4());token=new_token();b.create_session(sid,token)
            assert b.authenticate(sid,token) and not b.authenticate(sid,'wrong')
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda i:b.start_turn(str(uuid.uuid4()),sid,'fixture'),range(2)))
            assert results.count(None)==1 and results.count('session_busy')==1
            assert not a.rows('SELECT * FROM messages') and not a.rows('SELECT * FROM traces') and not a.rows('SELECT * FROM answer_cache')
            assert not b.rows("SELECT has_table_privilege(current_user,'"+schema+".messages','INSERT') AS can_write")[0]['can_write']
            b.set_cooldown(1)
            a.backup(Path('/tmp/landlaw-postgres-restore-backup.json'))
            payload=json.loads(Path('/tmp/landlaw-postgres-restore-backup.json').read_text())
            assert set(payload)=={'format','releases','state'}
            result={'passed':True,'checked_at':utcnow().isoformat(),'corpus_id':release['id'],'documents':59,
                'postgres_restore':True,'runtime_role_tested':True,'parallel_session_lease':True,'history_writes_revoked':True,
                'scope':'Isolated disposable schema using the existing owner/runtime roles; public service schema is never migrated or changed.'}
            Path('reports/postgres-restore.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result))
        finally:
            if a:a.close()
            if b:b.close()
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'passed':False,'error_type':type(error).__name__}))
        raise SystemExit(1) from None
