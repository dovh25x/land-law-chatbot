import json,re
from pathlib import Path
from landlaw.security import digest
s=json.loads(Path('data/sources.json').read_text());lookup={x['id']:x for x in s}
manifest={
 'luat-71-2025':[1,2,3,49,50],
 'luat-93-2025':[1,2,3,71,72,73],
 'luat-95-2025':[1,2,3,56,57,58,59],
 'luat-116-2025':[1,2,3,43,44,45],
 'luat-130-2025':[1,2,3,104,105,106,107],
 'luat-142-2025':[1,2,3,86,87,88,89],
}
# Candidate selection only; verify retained definitions, cross-references and
# operative effectivity before applying index_articles to active inputs.
r=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())
rows=[]
for ident,articles in manifest.items():
 d=next(d for d in r['documents'] if d['id']==ident)
 selected=[c for c in d['chunks'] if any(c['locator'].split(' · ')[0]==f'Điều {n}' for n in articles)]
 rows.append({'id':ident,'candidate_articles':articles,'original_chunks':len(d['chunks']),'selected_chunks':len(selected),
  'retained_locators':sorted({c['locator'] for c in selected}),'status':'pending_scope_review'})
 # Source excerpts for actual review, no embedding content duplicated.
 Path(f'data/raw/{ident}-scope-review.txt').write_text('\n\n'.join(c['id']+' '+c['locator']+'\n'+c['text'] for c in selected if not c['id'].endswith('parent')))
Path('reports/corpus-remediation-20261018/projection-candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
# Correct only three reviewed act-number spellings, retaining all table values.
source=lookup['qd-71-2024-hanoi'];fixes=[]
for filename in source['raw_paths']:
 checksum=digest(Path(filename).read_bytes());cache=Path('data/checkpoints')/f'parse-layout-v4-{checksum}.json'
 pages=json.loads(cache.read_text())['pages'];changed=0;texts=[]
 for number,text in pages:
  for pattern,replacement in [(r'(?<!\d)7[ \t]+1/2024', '71/2024'),(r'(?<!\d)3[ \t]+0/2019','30/2019'),(r'(?<!\d)2[ \t]+0/2023','20/2023')]:
   text,n=re.subn(pattern,replacement,text);changed+=n
  texts.append(text)
 if not changed:continue
 out=Path(filename).with_suffix('.act-numbers-reviewed.txt');out.write_text('\f'.join(texts))
 fixes.append({'ocr_path':str(out),'ocr_sha256':digest(out.read_bytes()),'pdf_sha256':checksum,
  'review_status':'verified','processing_method':'native layout; source act-number whitespace corrected only for 71/2024, 30/2019, 20/2023',
  'corrections':changed})
source['ocr_sidecars']=source.get('ocr_sidecars',[])+fixes
source['source_review_notes']=(source.get('source_review_notes') or '')+' Số hiệu 71/2024, 30/2019 và 20/2023 bị tách khoảng trắng được đối chiếu bản chụp tiêu đề và chuẩn hóa trong text; không nối hoặc sửa giá trị bảng.'
Path('data/sources.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
Path('reports/corpus-remediation-20261018/qd71-act-number-corrections.json').write_text(json.dumps({'scope':'Only the three title/source act numbers confirmed visually; table values unchanged.','sidecars':fixes},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'projection_candidates':rows,'number_corrections':sum(x['corrections'] for x in fixes)},ensure_ascii=False))
