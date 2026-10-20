import asyncio,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import httpx
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.ingest import collect_source
from landlaw.models import Document
from landlaw.provider import GroqProvider
from landlaw.store import Store
from landlaw.publication import validate_corpus
from landlaw.security import digest

async def main():
 root=Path('reports/production-finalization-20261020');raw=Path('data/raw/citizen-finalization-20261020');stamp=datetime.now(timezone.utc).isoformat()
 url='https://datafiles.hanoi.gov.vn/gov-hni/6974/VanBan/2026/1/26/Th%C3%B4ng%20b%C3%A1o%20chuy%E1%BB%83n%20tr%E1%BB%A5%20s%E1%BB%9F%20TCD%20TP.pdf'
 pub='https://xuandinh.hanoi.gov.vn/van-ban-chi-dao-dieu-hanh/thong-bao-ve-viec-chuyen-tru-so-tiep-cong-dan-thanh-pho-va-tru-so-lam-viec-cua-ban-tiep-cong-dan-th-233519'
 news='https://cmshn.hanoi.gov.vn/tin-tuc-su-kien-noi-bat/chu-tich-ubnd-thanh-pho-vu-dai-thang-tiep-cong-dan-dinh-ky-thang-4-2026-426042115193111.htm'
 async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
  responses=await asyncio.gather(*(client.get(u) for u in [url,pub,news]));receipts=[]
  for key,u,r in zip(['city-directory-refetched','city-directory-publication','city-directory-corroboration'],[url,pub,news],responses):
   r.raise_for_status();p=raw/(key+'-v2'+('.pdf' if key.endswith('refetched') else '.html'));p.write_bytes(r.content);receipts.append({'url':u,'resolved_url':str(r.url),'status':r.status_code,'raw_path':str(p),'sha256':digest(r.content)})
  assert receipts[0]['sha256']=='4e3da283f05e23c8b89f25c76433f8640192737534c25bcdcab888d8f7bd916e'
  from bs4 import BeautifulSoup
  assert '349' in BeautifulSoup(responses[2].text,'html.parser').get_text() and 'Phố Huế' in BeautifulSoup(responses[2].text,'html.parser').get_text()
  source={'id':'hanoi-reception-relocation-2026','title':'Địa điểm Trụ sở Tiếp công dân Thành phố Hà Nội','source_kind':'official_directory',
   'url':url,'publication_url':pub,'metadata_url':pub,'attachment_urls':[url],
   'raw_paths':[receipts[0]['raw_path']],'raw_checksums':{receipts[0]['raw_path']:receipts[0]['sha256']},
   'jurisdiction':'Hanoi','project':'ring4','issuer':'Văn phòng UBND thành phố Hà Nội','issued_on':'2026-01-26','effective_from':'2026-01-26','effective_to':None,
   'document_number':None,'topics':['liên hệ','tiếp công dân'],'task_tags':['find_contact'],
   'administrative_scope':'Trụ sở tiếp công dân cấp thành phố Hà Nội; không xác định thẩm quyền giải quyết hồ sơ cá nhân.',
   'review_status':'verified','checked_at':stamp,'public_contacts_reviewed':True,'contains_personal_data':False,
   'source_review_notes':'AI technical source review of the entire one-page native PDF and official publication/corroboration, not independent legal certification. Address only: 349 phố Huế, phường Hai Bà Trưng, Hà Nội, from26/01/2026. No phone, opening hours, submission channel or deciding competence is proven. Blank attachment number/date means no document_number is asserted. Official names in institutional signature are not claimant data. A future activation still requires current operational receipt and model/retrieval checks.',
   'operational_review_status':'pending','required_dependency_ids':[]}
  # A reviewed source proposal is prepared, never inserted into active manifest/DB.
  doc=await collect_source(source,Settings(),client,offline=True,allow_ocr=False)
  assert any('349' in c.text and 'Huế' in c.text for c in doc.chunks)
  stage=Path('data/staging/citizen-directory-candidate-20261020');stage.mkdir(parents=True,exist_ok=False)
  (stage/'source-proposal.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
  (stage/'parsed-document.json').write_text(doc.model_dump_json(indent=2))
  result={'checked_at':stamp,'review_method':'AI technical full one-page PDF/publication/corroboration review; no independent legal certification',
   'source':source,'fetches':receipts,'parsed_chunks':len(doc.chunks),'stage':str(stage),'active_manifest_changed':False,'active_corpus_changed':False,'vectors_generated':0,
   'allowed_fact':'Public institutional address only, effective26/01/2026; do not assert the receiving/deciding office for a particular complaint.',
   'remaining':['Current operational receipt at activation','Additive corpus candidate preserving existing vectors','Retrieval and model evaluation bound to candidate corpus before activation']}
  (root/'city-directory-source-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'parsed_chunks':len(doc.chunks),'stage':str(stage),'serving_changed':False}))
asyncio.run(main())
