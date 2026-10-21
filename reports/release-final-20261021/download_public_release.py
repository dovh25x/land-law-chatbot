"""Anonymous public release download + byte verification; never calls model APIs."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

TAG='v0.1.0-academic-20261021'
BASE='https://github.com/dovh25x/land-law-chatbot/releases/download/'+TAG+'/'
LOCAL=Path('dist/academic-release-20261021')
OUT=Path('dist/public-release-download-20261021')
if OUT.exists():raise ValueError('Preserve prior public download evidence')
OUT.mkdir(parents=True)
checks=[]
with httpx.Client(timeout=60,follow_redirects=True) as client:
    sums=client.get(BASE+'SHA256SUMS');assert sums.status_code==200
    assert sums.content==(LOCAL/'SHA256SUMS').read_bytes()
    (OUT/'SHA256SUMS').write_bytes(sums.content)
    for line in sums.text.splitlines():
        digest,name=line.split('  ',1)
        assert re.fullmatch('[0-9a-f]{64}',digest) and re.fullmatch('[A-Za-z0-9_.-]+',name)
        assert (LOCAL/name).is_file()
        h=hashlib.sha256();size=0
        with client.stream('GET',BASE+name) as response:
            assert response.status_code==200
            with (OUT/name).open('xb') as output:
                for part in response.iter_bytes():
                    size+=len(part);assert size<=50_000_000
                    h.update(part);output.write(part)
        assert h.hexdigest()==digest==hashlib.sha256((LOCAL/name).read_bytes()).hexdigest()
        row={'asset':name,'bytes':size,'sha256':digest,'status':'PASS'}
        checks.append(row);print(json.dumps(row),flush=True)
receipt={'status':'PASS','checked_at':datetime.now(UTC).isoformat(),'release_tag':TAG,'anonymous_download':True,'authorization_headers_sent':False,'assets':checks,'contains_private_data':False,'scope':'Public release HTTP downloads and SHA256 integrity only; corpus restore is verified in a separate isolated-database receipt.'}
(OUT/'public-download-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'PASS','downloaded_assets':len(checks),'directory':str(OUT)}))
