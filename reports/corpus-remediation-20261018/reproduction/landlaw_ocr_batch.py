import concurrent.futures,json,os,subprocess,tempfile
from pathlib import Path
import pypdfium2
from landlaw.security import digest
jobs=[('ring4-nq106-2022','data/raw/ring4-nq106-2022-remediation-live-1.pdf',None),('qd-10-2017-hanoi','data/raw/qd-10-2017-hanoi-new-official-1.pdf',None),('nd-01-2017','data/raw/nd-01-2017-new-official-1.pdf',None),('qd-30-2019-hanoi','data/raw/qd-30-2019-hanoi-remediation-live-1.pdf',list(range(1,11))),('nd-123-2024','data/raw/nd-123-2024-remediation-live-1.pdf',None),('nd-148-2020','data/raw/nd-148-2020-alternate.pdf',None)]
env={**os.environ,'OMP_THREAD_LIMIT':'1','LD_LIBRARY_PATH':'/tmp/landlaw-ocr/usr/lib/x86_64-linux-gnu','TESSDATA_PREFIX':'/tmp/landlaw-ocr/usr/share/tesseract-ocr/5/tessdata'}
all_reports=[]
for ident,name,selection in jobs:
 out=Path(f'data/raw/{ident}-remediation-ocr.txt')
 if out.exists():continue
 pdf=pypdfium2.PdfDocument(name);pages=selection or list(range(1,len(pdf)+1));count=len(pdf)
 with tempfile.TemporaryDirectory(prefix='landlaw-ocr-') as tmp:
  folder=Path(tmp)
  for number in pages:
   p=pdf[number-1];b=p.render(scale=3);b.to_pil().save(folder/f'{number}.png');b.close();p.close()
  def ocr(number):
   proc=subprocess.run(['/tmp/landlaw-ocr/usr/bin/tesseract',str(folder/f'{number}.png'),'stdout','-l','vie','--psm','3'],env=env,capture_output=True,check=True,timeout=120)
   return proc.stdout.decode()
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:texts=list(pool.map(ocr,pages))
 pdf.close();out.write_text('\f'.join(texts))
 report={'document_id':ident,'pdf_path':name,'pdf_sha256':digest(Path(name).read_bytes()),'pdf_pages':count,'indexed_pages':pages,'output':str(out),'ocr_sha256':digest(out.read_bytes()),'review_status':'pending','characters_by_page':[len(t) for t in texts],'engine':'Tesseract 5.5.0 vie psm3 @216dpi'}
 all_reports.append(report);Path(f'data/raw/{ident}-remediation-ocr-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'ocr':ident,'pages':len(pages),'minimum_characters':min(len(t) for t in texts)}),flush=True)
Path('reports/corpus-remediation-20261018/ocr-candidates.json').write_text(json.dumps(all_reports,ensure_ascii=False,indent=2)+'\n')
