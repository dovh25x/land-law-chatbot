import json
from pathlib import Path
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.security import utcnow
r=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())
s=Store(Settings())
try:
 rows=s.rows('SELECT id,document_id,checksum,embedding_model FROM chunks WHERE release_id=?',(r['id'],))
 expected={c['id']:(c['document_id'],c['checksum'],c['embedding_model']) for d in r['documents'] for c in d['chunks']}
 actual={c['id']:(c['document_id'],c['checksum'],c['embedding_model']) for c in rows}
 result={'checked_at':utcnow().isoformat(),'corpus_id':r['id'],'postgresql_chunks':len(rows),'snapshot_chunks':len(expected),
  'all_chunk_ids_checksums_and_embedding_models_match':actual==expected,'missing_ids':sorted(expected.keys()-actual.keys()),'unexpected_ids':sorted(actual.keys()-expected.keys()),
  'mismatched_ids':sorted(k for k in actual.keys()&expected.keys() if actual[k]!=expected[k]),
  'scope':'Read-only metadata equality; stored PostgreSQL text and vector bytes are not independently rehashed.'}
 Path('reports/corpus-audit-20261018-e1db9ef/postgresql-chunk-integrity.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if not k.endswith('ids')}))
finally:s.close()
