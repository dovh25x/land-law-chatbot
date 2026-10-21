"""Verify downloaded release assets by restoring only into a NEW local PostgreSQL DB."""
import argparse
import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.store import Store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    assert 1024 <= args.port <= 65535 and not args.receipt.exists()
    root=args.directory
    manifest=json.loads((root/'corpus-manifest.json').read_text())
    source=root/'corpus-backup.json'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['sha256']
    payload=json.loads(source.read_text())
    expected=next(Store.decode_release(r['payload']) for r in payload['releases'] if r['id']==manifest['corpus_id'])
    ident='landlaw_asset_'+uuid.uuid4().hex[:10]
    with psycopg.connect(f'host=127.0.0.1 port={args.port} dbname=landlaw_phase4 user=postgres',autocommit=True) as connection:
        assert connection.execute('SELECT current_database()').fetchone()[0]=='landlaw_phase4'
        connection.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(ident)))
    dsn=f'host=127.0.0.1 port={args.port} dbname={ident} user=postgres'
    with psycopg.connect(dsn,autocommit=True) as connection:
        for path in sorted(Path('migrations').glob('*.sql')):connection.execute(path.read_text())
    store=Store(Settings(_env_file=None,database_url=dsn,admin_database_url='',groq_api_key='',source_lookup_only=True,generation_enabled=False,allow_stale_generation=False))
    try:
        assert not store.rows('SELECT id FROM releases')
        store.restore(source)
        actual=store.release()
        assert actual['id']==expected['id'] and actual['documents']==expected['documents']
        legal=Path('reports/phase2c-current-20261021')
        receipts=[record_source_review(store,p) for p in sorted((legal/'receipts-final').glob('*.json'))]
        gate=activate_source_gate(store,legal/'source-gate-final.json')
        passages=[(d['id'],c['id'],c['checksum']) for d in actual['documents'] for c in d['chunks']]
        reviews=store.scoped_source_reviews(store.release(None,True),passages,date(2026,10,21))
        assert sum(v=='fresh' for v in reviews.values())==43
        counts={t:store.rows('SELECT count(*) AS n FROM '+t)[0]['n'] for t in ('documents','chunks','sessions','turns','messages','traces','answer_cache')}
        assert all(counts[t]==0 for t in ('sessions','turns','messages','traces','answer_cache'))
        result={'status':'PASS','checked_at':datetime.now(UTC).isoformat(),'downloaded_asset_sha256':manifest['sha256'],'source_commit':manifest['source_commit'],'corpus_id':actual['id'],'retained_private_database':ident,'postgres_major':16,'counts':counts,'exact_documents_roundtrip':True,'receipt_count':len(receipts),'fresh_passages_2026_10_21':43,'source_gate':gate,'production_mutated':False,'external_llm_requests':0,'scope':'Downloaded GitHub Release corpus asset, checksum verified, new local database only; legal receipt bundle from pinned source release.'}
        args.receipt.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:store.close()


if __name__=='__main__':main()
