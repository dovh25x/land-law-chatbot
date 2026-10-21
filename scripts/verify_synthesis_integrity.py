"""Capture the real bounded synthesis input on isolated SQLite, without inference.

Draft requests return an explicit abstention. No scripted legal answer or judge
can create a PASS: assertions inspect the payload actually delivered to generate.
All expected source text comes from the retained acceptance/corpus artifacts.
"""
import argparse
import asyncio
import hashlib
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx

from landlaw.agent import Agent, Plan, ToolCall, model_passage_text, quote_matches, source_clause_spans
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import ChatRequest, Draft
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.security import utcnow
from landlaw.store import Store
from scripts.verify_source_gate_candidate import OfflineProvider


def source_paragraph(text, number):
    formatted=model_passage_text(text)
    spans=source_clause_spans(formatted)
    span=next(s for s in spans if s['number']==str(number))
    return formatted[span['start']:span['end']].strip()


def required_sources(cases, documents):
    """Evidence assertions, not answer golds. Do not inject these into retrieval."""
    chunks={c['id']:c for d in documents for c in d['chunks']}
    # Exact original paragraphs reviewed in Phase2C. These are acceptance
    # expectations only; runtime code never imports IDs or this manifest.
    specs={
        'C01': [('luat-dat-dai-2024-97-1-0',None),
                ('luat-dat-dai-2024-98-0-parent','2'),
                ('luat-dat-dai-2024-100-2-0','1'),
                ('nq-254-2025-2-0-1','10')],
        'C02': [('luat-dat-dai-2024-106-1-0','1'),
                ('qd-40-2026-hanoi-9-1-parent','1'),
                ('nd-49-2026-11-0-parent','6')],
        'C03': [('qd-40-2026-hanoi-12-1-0',None),
                ('qd-40-2026-hanoi-13-0-0','2'),
                ('qd-40-2026-hanoi-13-0-0','3'),
                ('luat-dat-dai-2024-110-scope-4',None),
                ('nd-88-2024-0-11-parent','2'),
                ('nd-226-2025-34-scope-7-2a-5',None),
                ('nd-49-2026-23-scope-16-3g',None)],
    }
    result={}
    for case in cases:
        result[case['id']]=[]
        for ident,paragraph in specs.get(case['id'],[]):
            chunk=chunks[ident]
            text=source_paragraph(chunk['text'],paragraph) if paragraph else chunk['text']
            # A section heading after the last source paragraph is not a rule.
            import re
            text=re.split(r'\s+Mục\s+\d+\s+[A-ZĐÀ-Ỹ][A-ZĐÀ-Ỹ,\s]{10,}$',text,maxsplit=1)[0].strip()
            result[case['id']].append({'source_id':ident,'document_id':chunk['document_id'],
                'locator':chunk['locator'].split(' · ')[0], 'paragraph':paragraph,
                'source_checksum':chunk['checksum'],'text':text,
                'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
    return result


class CaptureProvider(OfflineProvider):
    def __init__(self,settings,encoder):
        super().__init__(settings,encoder)
        self.payloads=[]
    async def generate(self,schema,instruction,payload,budget):
        budget.llm()
        if schema is Plan:
            return Plan(tools=[ToolCall(name='search_law',query=payload['question'][:1000])])
        if schema is not Draft:
            raise AssertionError('No fake judge is permitted in synthesis-input acceptance')
        self.payloads.append(json.loads(json.dumps(payload,ensure_ascii=False)))
        return Draft(status='insufficient_evidence')


async def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    paths=[args.candidate,args.cases,args.policy,*sorted(args.receipts.glob('*.json')),
           Path(__file__),*sorted(Path('backend/landlaw').glob('*.py'))]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    candidate=json.loads(args.candidate.read_text())
    cases=json.loads(args.cases.read_text())
    expected=required_sources(cases['cases'],candidate['documents'])
    (args.output/'required-evidence.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2)+'\n')
    for name,checksum in [('model_quantized.onnx',MODEL['onnx_sha256']),('sentencepiece.bpe.model',MODEL['tokenizer_sha256'])]:
        if Encoder.file_sha(Path('models/e5')/name)!=checksum:raise ValueError('Pinned local model required; no downloads')
    encoder=Encoder(Path('models/e5'))
    results=[]
    with tempfile.TemporaryDirectory(prefix='landlaw-phase2d-') as folder:
        settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',
                          groq_api_key='',allow_stale_generation=False,sqlite_path=str(Path(folder)/'candidate.db'))
        store=Store(settings)
        runtime=configuration_fingerprint(settings)
        try:
            store.stage(candidate);store.publish(candidate['id'])
            for p in sorted(args.receipts.glob('*.json')):record_source_review(store,p)
            activate_source_gate(store,args.policy)
            for case in cases['cases']:
                capture={}
                class RecordingAgent(Agent):
                    async def finish(self,state):
                        capture.update(retrieval=state.get('retrieval_diagnostics',{}),
                            retained_context=self.context(state),
                            diagnostics=state.get('synthesis_diagnostics',{}),
                            synthesis_sources=state.get('synthesis_sources',{}),
                            synthesis_origin=state.get('synthesis_origin','none'))
                        return await super().finish(state)
                provider=CaptureProvider(settings,encoder)
                async def emit(event):pass
                answer=await RecordingAgent(store,provider).run(ChatRequest(session_id='0'*36,
                    message=case['question'],as_of=date.fromisoformat(case.get('as_of',cases['as_of']))),emit)
                payload=provider.payloads[-1] if provider.payloads else None
                shown=[] if payload is None else payload['evidence']
                checks=[]
                for requirement in expected[case['id']]:
                    matches=[x['citation_id'] for x in shown if x['document_id']==requirement['document_id']
                        and x['locator'].split(' · ')[0]==requirement['locator']
                        and quote_matches(requirement['text'],x['text'])]
                    checks.append({**{k:v for k,v in requirement.items() if k!='text'},
                                   'present':bool(matches),'synthesis_aliases':matches})
                wire_chars=0 if not payload else len(json.dumps([shown,payload['documents']],ensure_ascii=False,separators=(',',':')))
                ledger=capture.get('synthesis_sources',{})
                aliases={f'C{i+1}':source for i,source in enumerate(ledger.values())}
                exact_wire=payload is None or all(x['citation_id'] in aliases and x['text']==aliases[x['citation_id']]['text'] for x in shown)
                row={'id':case['id'],'question':case['question'],'as_of':case.get('as_of',cases['as_of']),
                    'kind':'actual_pipeline_synthesis_input_no_inference','model_pass':None,'external_llm_requests':0,
                    'external_llm_tokens':0,'output_status':answer.status,'output_citations':[c.id for c in answer.citations],
                    'source_requirements':checks,'complete':bool(checks) and all(c['present'] for c in checks),
                    'wire_context_chars':wire_chars,'within_context_limit':wire_chars<=7000,
                    'ledger_matches_actual_wire':exact_wire,'synthesis_requests_captured':len(provider.payloads),
                    'synthesis_payload':payload,**capture}
                results.append(row)
                with (args.output/'attempts.jsonl').open('a') as out:
                    out.write(json.dumps(row,ensure_ascii=False)+'\n')
                print(json.dumps({k:row[k] for k in ('id','complete','wire_context_chars','ledger_matches_actual_wire','output_status')},ensure_ascii=False),flush=True)
            unchanged=hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            report={'checked_at':utcnow().isoformat(),'storage_backend':'isolated_sqlite','corpus_id':candidate['id'],
                'runtime_fingerprint':runtime,'runtime_unchanged':runtime==configuration_fingerprint(settings),
                'input_sha256':hashes,'inputs_unchanged':unchanged,'external_llm_requests':0,'model_pass':None,
                'scope':'Actual synthesis payload capture, no generated legal answers, no semantic judge.',
                'all_three_complete':all(r['complete'] for r in results[:3]),'cases':results}
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','cases','policy','receipts','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    def forbid(*a,**k):raise AssertionError('External HTTP forbidden in Phase2D')
    async def async_forbid(*a,**k):raise AssertionError('External HTTP forbidden in Phase2D')
    with patch.object(httpx.Client,'send',forbid),patch.object(httpx.AsyncClient,'send',async_forbid):
        asyncio.run(run(args))


if __name__=='__main__':main()
