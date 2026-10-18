import json
from pathlib import Path
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.security import utcnow
from landlaw.evaluation import configuration_fingerprint
s=Settings()
r={'checked_at':utcnow().isoformat(),'scope':'Read-only deployed database metadata and freshness, no content or credentials logged.'}
st=None
try:
 st=Store(s)
 release=st.release(None,True)
 r.update({'backend':'postgresql' if st.postgres else 'sqlite','corpus_id':(release or {}).get('id'),'configuration_sha256':configuration_fingerprint(s)})
 if release:
  r['documents']=[{'id':d['id'],'checksum':d['checksum'],'checked_at':d['checked_at']} for d in release['documents']]
  r['release_checked_at']=release['checked_at']
  r['source_fresh']=st.source_fresh(release)
  r['counts']=st.rows('SELECT source_kind,project,COUNT(*) AS count FROM documents WHERE release_id=? GROUP BY source_kind,project',(release['id'],))
  r['chunk_count']=st.rows('SELECT COUNT(*) AS count FROM chunks WHERE release_id=?',(release['id'],))[0]['count']
  r['reviews']=st.rows('SELECT document_id,checksum,checked_at,status FROM source_reviews WHERE release_id=? ORDER BY checked_at DESC',(release['id'],))
except Exception as e:
 r['error_type']=type(e).__name__
finally:
 if st:st.close()
Path('reports/corpus-audit-20261018-e1db9ef/production-metadata.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in {'documents','reviews'}},ensure_ascii=False))
