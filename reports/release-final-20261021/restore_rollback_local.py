"""Restore the pre-deploy cloud corpus into a fresh, retained local PG database."""
import argparse
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.store import Store


def main(port):
    out=Path(__file__).parent
    receipt=json.loads((out/'before-deploy-backup.json').read_text())
    source=Path(receipt['file'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==receipt['sha256']
    payload=json.loads(source.read_text())
    active=receipt['active_corpus']
    expected=next(Store.decode_release(r['payload']) for r in payload['releases'] if r['id']==active)
    name='landlaw_rollback_'+uuid.uuid4().hex[:10]
    assert 1024<=port<=65535
    control=f'host=127.0.0.1 port={port} dbname=landlaw_phase4 user=postgres connect_timeout=5'
    with psycopg.connect(control,autocommit=True) as connection:
        assert connection.execute('SELECT current_database()').fetchone()[0]=='landlaw_phase4'
        connection.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(name)))
    dsn=f'host=127.0.0.1 port={port} dbname={name} user=postgres connect_timeout=5'
    with psycopg.connect(dsn,autocommit=True) as connection:
        for path in sorted(Path('migrations').glob('*.sql')):
            connection.execute(path.read_text())
    store=Store(Settings(_env_file=None, database_url=dsn, admin_database_url='',groq_api_key='',allow_stale_generation=False))
    try:
        store.restore(source)
        actual=store.release()
        assert actual['id']==active and actual['documents']==expected['documents']
        counts={t:store.rows('SELECT count(*) AS n FROM '+t)[0]['n'] for t in ('documents','chunks','sessions','turns','messages','traces','answer_cache')}
        assert all(counts[t]==0 for t in ('sessions','turns','messages','traces','answer_cache'))
        assert counts['documents']==len(expected['documents'])
        assert counts['chunks']==sum(len(d['chunks']) for d in expected['documents'])
        result={'status':'PASS','checked_at':datetime.now(UTC).isoformat(),'backup_sha256':receipt['sha256'],
            'active_corpus':active,'isolated_local_database':name,'retained':True,'production_database_mutated':False,
            'exact_document_roundtrip':True,'counts':counts,'no_conversations_or_sessions_restored':True,
            'scope':'Cloud corpus/config backup restored into fresh local PG16; current cloud PG17 schema/role inspected separately. No serving overwrite or DROP.'}
        target=out/'rollback-restore.json'
        if target.exists():
            raise ValueError('Preserve previous restore evidence')
        target.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,required=True)
    main(parser.parse_args().port)
