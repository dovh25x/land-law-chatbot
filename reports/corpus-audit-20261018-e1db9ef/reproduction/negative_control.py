import asyncio,importlib.util,json,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('corpus_audit','scripts/audit_corpus.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
async def main():
 release=json.loads(Path('data/releases/corpus-581da76c79b0b362.json').read_text())
 target=release['documents'][0]['chunks'][0]
 target['text'] += ' Controlled corruption for audit validation.'
 with tempfile.TemporaryDirectory(prefix='landlaw-audit-negative-') as folder:
  path=Path(folder)/'corrupted-snapshot.json';path.write_text(json.dumps(release,ensure_ascii=False))
  output=Path(folder)/'report.json'
  failed=await module.audit(path,output,False)
  report=json.loads(output.read_text())
  detected=any(x['kind']=='chunk_integrity' and x['chunk_id']==target['id'] for x in report['errors'])
  assert failed and detected
  saved={'fixture':'Temporary copy with one deliberately corrupted public-law chunk text; active snapshot unchanged.',
   'passed':True,'audit_failed_as_expected':bool(failed),'corruption_detected_at_chunk_id':target['id'],
   'detected_errors':report['errors'],'scope':'Negative control for checksum detection, not legal quality or a corpus attempt.'}
  Path('reports/corpus-audit-20261018-e1db9ef/negative-control.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps(saved,ensure_ascii=False))
asyncio.run(main())
