"""Controlled comparison: same retained evidence, baseline vs current packing.

Baseline is preserved Phase2C code. All calls are local; no model/database calls.
"""
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from landlaw.agent import quote_matches
from landlaw.config import Settings
from landlaw.models import ChatRequest,Document,Evidence

base=Path('reports/phase2d-synthesis-20261021')
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('landlaw.phase2d_baseline',base/'baseline/backend/landlaw/agent.py')
legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
report=json.loads((base/'acceptance-locked/report.json').read_text())
requirements=json.loads((base/'acceptance-locked/required-evidence.json').read_text())
payload=json.loads(Path('data/staging/phase2c-current/release-v5.json').read_text())
documents={d['id']:Document.model_validate(d) for d in payload['documents']}
chunks={c.id:c for d in documents.values() for c in d.chunks}
results=[]
for case in report['cases'][:3]:
    state={'evidence':[Evidence(document=documents[x['document_id']],chunk=chunks[x['citation_id']],
        applicability=x['applicability']) for x in case['retained_context']],
        'release':payload,'as_of':date.fromisoformat(case['as_of']),
        'request':ChatRequest(session_id='0'*36,message=case['question'])}
    passages,docs=legacy.Agent(None,SimpleNamespace(settings=Settings(_env_file=None))).prompt_context(state)
    old=[]
    for req in requirements[case['id']]:
        present=[x['citation_id'] for x in passages if x['document_id']==req['document_id']
            and x['locator'].split(' · ')[0]==req['locator'] and quote_matches(req['text'],x['text'])]
        old.append({'source_id':req['source_id'],'paragraph':req['paragraph'],
                    'text_sha256':req['text_sha256'],'present':bool(present),'shown_ids':present})
    row={'id':case['id'],'same_retained_evidence':True,'before_sources':[p['citation_id'] for p in passages],
         'before_complete_required_units':all(x['present'] for x in old),'before_checks':old,
         'before_missing':[{'source_id':x['source_id'],'paragraph':x['paragraph']} for x in old if not x['present']],
         'after_sources':case['diagnostics']['synthesis_sources'],
         'after_complete_required_units':case['complete'],'after_wire_context_chars':case['wire_context_chars'],
         'after_missing':[{'source_id':x['source_id'],'paragraph':x['paragraph']} for x in case['source_requirements'] if not x['present']]}
    results.append(row)
value={'scope':'Controlled packer-only comparison on the same actual retained evidence. No model answer pass.',
    'model_pass':None,'external_llm_requests':0,
    'note':'Phase2D also checks the ND49 authority dependency for C02. The earlier 1/3 figure checked only fixture-cited source content, which omitted that dependency.',
    'results':results}
(base/'before-after.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ('id','before_missing','after_complete_required_units','after_wire_context_chars')} for r in results],ensure_ascii=False))
