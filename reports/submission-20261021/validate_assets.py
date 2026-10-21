"""Read exported assets; write validation for documents, not model/deployment quality."""
from pathlib import Path
import json, hashlib, re
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from pypdf import PdfReader
BASE=Path(__file__).resolve().parent
results={'scope':'Academic export QA only; not model, legal or public E2E validation','pdf':{},'pptx':{},'errors':[]}
for name,expected in [('Final_Project_Report.pdf',None),('Final_Project_Presentation.pdf',12)]:
 path=BASE/name
 if not path.exists():results['errors'].append('Missing '+name);continue
 reader=PdfReader(path);texts=[p.extract_text() for p in reader.pages];fonts=set();unembedded=set()
 for p in reader.pages:
  for ref in p.get('/Resources',{}).get('/Font',{}).values():
   font=ref.get_object();fonts.add(str(font.get('/BaseFont')))
   desc=font.get('/FontDescriptor')
   if not desc and font.get('/DescendantFonts'):desc=font['/DescendantFonts'][0].get_object().get('/FontDescriptor')
   if desc:
    desc=desc.get_object()
    if not any(key in desc for key in ['/FontFile','/FontFile2','/FontFile3']):unembedded.add(str(font.get('/BaseFont')))
 joined='\n'.join(texts)
 entry={'pages':len(reader.pages),'page_sizes_points':sorted({(round(float(p.mediabox.width),2),round(float(p.mediabox.height),2)) for p in reader.pages}),'embedded_fonts':sorted(fonts),'unembedded_detected':sorted(unembedded),'text_chars':len(joined),'blank_pages':[i+1 for i,t in enumerate(texts) if len(t.strip())<40],'contains_vietnamese':all(s in joined for s in ['nguồn','pháp luật']),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 uris=[]
 for p in reader.pages:
  for ref in p.get('/Annots',[]):
   annotation=ref.get_object();action=annotation.get('/A')
   if action:action=action.get_object()
   if action and action.get('/URI'):uris.append(str(action['/URI']))
 local_uris=[uri for uri in uris if uri.lower().startswith('file:') or '/home/' in uri or 'localhost' in uri or '127.0.0.1' in uri]
 entry['link_annotations']={'uri_count':len(uris),'local_uris':local_uris,'public_links':sorted(set(uris)),'http_reachability':'NOT TESTED during offline export; stable tag is published after assets are generated'}
 if local_uris:results['errors'].append(name+': nonportable local links')
 results['pdf'][name]=entry
 if expected and len(reader.pages)!=expected:results['errors'].append(f'{name}: expected {expected} pages, got {len(reader.pages)}')
 if entry['blank_pages']:results['errors'].append(name+': blank pages')
 if not entry['contains_vietnamese']:results['errors'].append(name+': Vietnamese extraction missing')
 if unembedded:results['errors'].append(name+': unembedded font')
 if 'Report' in name:
  required=['97,37%','95,24%','S06','INCOMPLETE','NOT RUN','LlamaIndex','LangGraph','Groq']
  entry['required_text']={w:w in joined for w in required}
  if not all(entry['required_text'].values()):results['errors'].append(name+': required disclosure missing')
  (BASE/'report-page-text.json').write_text(json.dumps([{'page':i+1,'chars':len(t),'head':t[:160]} for i,t in enumerate(texts)],ensure_ascii=False,indent=2)+'\n')
pptx=BASE/'Final_Project_Presentation.pptx'
if pptx.exists():
 with ZipFile(pptx) as z:
  slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
  notes=[n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)]
  ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
  texts=[' '.join(ET.fromstring(z.read(n)).itertext()) for n in sorted(slides)]
  results['pptx']={'slides':len(slides),'notes':len(notes),'zip_test':z.testzip(),'has_architecture_image':any(n.startswith('ppt/media/') for n in z.namelist()),'sha256':hashlib.sha256(pptx.read_bytes()).hexdigest()}
  if len(slides)!=12 or len(notes)!=12:results['errors'].append('PPTX count/notes mismatch')
  if not results['pptx']['has_architecture_image']:results['errors'].append('PPTX architecture image missing')
else:results['errors'].append('Missing PPTX')
layout=BASE/'layout-check.json'
if layout.exists():
 results['html_layout']=json.loads(layout.read_text())
 for slide in results['html_layout'].get('slide_layout',[]):
  if slide['content_overflow']:results['errors'].append(f'Slide {slide["slide"]} HTML overflow: '+str(slide['content_overflow']))
# Validate package-relative Markdown links, without browsing external URLs or credentials.
missing=[]
for path in BASE.glob('*.md'):
 for dest in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text()):
  if dest.startswith(('http:','https:','mailto:','#')):continue
  target=(path.parent/dest.split('#')[0]).resolve()
  if not target.exists():missing.append({'file':path.name,'target':dest})
results['missing_local_links']=missing
if missing:results['errors'].append('Missing local links')
# Reject stale PDFs when status/prose or the renderer changed after the build.
try:
 build_path=BASE/'build-source-identity.json';build=json.loads(build_path.read_text())
 exported=json.loads((BASE/'export-identity.json').read_text());mismatches=[]
 for name,digest in {**build['inputs_sha256'],**build['generated_sha256']}.items():
  if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:mismatches.append(name)
 if hashlib.sha256(build_path.read_bytes()).hexdigest()!=exported['build_source_identity_sha256']:mismatches.append('export references another build')
 for name,digest in exported['pdf_sha256'].items():
  if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:mismatches.append(name)
 results['source_export_provenance']={'status':'PASS' if not mismatches else 'FAIL','mismatches':mismatches,'build_source_identity_sha256':hashlib.sha256(build_path.read_bytes()).hexdigest()}
 if mismatches:results['errors'].append('Stale source/export provenance')
except (OSError,KeyError,ValueError) as exc:
 results['source_export_provenance']={'status':'FAIL','reason':str(exc)};results['errors'].append('Missing source/export provenance')
# PDFium coordinates independently catch glyphs clipped outside a PDF page.
try:
 import pypdfium2 as pdfium
 results['pdf_bounds']={}
 for name in results['pdf']:
  doc=pdfium.PdfDocument(BASE/name);bad=[];chars=0
  for page_i,page in enumerate(doc):
   tp=page.get_textpage();width,height=page.get_size()
   for char_i in range(tp.count_chars()):
    chars+=1;bounds=tp.get_charbox(char_i)
    if bounds[0]<-1 or bounds[1]<-1 or bounds[2]>width+1 or bounds[3]>height+1:bad.append({'page':page_i+1,'character':char_i,'bounds':bounds})
  results['pdf_bounds'][name]={'chars_checked':chars,'outside_page_boxes':bad}
  if bad:results['errors'].append(name+': clipped PDF text')
except ImportError:
 results['pdf_bounds']='NOT TESTED — optional PDFium unavailable'
results['status']='PASS' if not results['errors'] else 'FAIL'
(BASE/'asset-validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
(BASE/'DELIVERABLES_SHA256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BASE.iterdir()) if p.is_file() and p.suffix in {'.pdf','.pptx'}},indent=2)+'\n')
print(json.dumps({'status':results['status'],'pdf_pages':{k:v['pages'] for k,v in results['pdf'].items()},'pptx_slides':results['pptx'].get('slides'),'errors':results['errors']},ensure_ascii=False))
raise SystemExit(bool(results['errors']))
