"""Isolated SQLite acceptance using real retrieval/gates and explicit draft/judge fixtures.

No Groq/network calls. Fixture acceptance cannot establish model correctness or
faithfulness. Retain failed local attempts; use a new output folder for each run.
"""
import argparse
import asyncio
import hashlib
import json
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx

from landlaw.agent import Agent, Plan, ToolCall, Verification
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import ChatRequest, Claim, Draft
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.security import utcnow
from landlaw.store import Store
from scripts.verify_source_gate_candidate import OfflineProvider


class FixtureProvider(OfflineProvider):
    def __init__(self, settings, encoder, claims):
        super().__init__(settings, encoder, fixture=True)
        self.claims = claims
        self.fixture_outputs = []

    async def generate(self, schema, instruction, payload, budget):
        if schema is Draft:
            budget.llm()
            self.fixture_calls += 1
            value = Draft(status='answered' if self.claims else 'insufficient_evidence',
                          claims=[Claim(**c) for c in self.claims])
        elif schema is Plan:
            budget.llm()
            self.fixture_calls += 1
            value = Plan(tools=[ToolCall(name='search_law', query=payload['question'][:1000])])
        elif schema is Verification:
            value = await super().generate(schema, instruction, payload, budget)
        else:
            raise RuntimeError('Unscripted planner/model call is disabled')
        self.fixture_outputs.append({'schema': schema.__name__, 'result': value.model_dump(mode='json')})
        return value


async def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    paths = [args.candidate, args.cases, args.policy, *sorted(args.receipts.glob('*.json')), Path(__file__),
             *sorted(Path('backend/landlaw').glob('*.py'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    cases = json.loads(args.cases.read_text())
    payload = json.loads(args.candidate.read_text())
    for name, checksum in [('model_quantized.onnx', MODEL['onnx_sha256']),
                           ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
        path = Path('models/e5')/name
        if not path.is_file() or Encoder.file_sha(path) != checksum:
            raise ValueError('Pinned local model required; downloads disabled')
    encoder = Encoder(Path('models/e5'))
    records = []
    with tempfile.TemporaryDirectory(prefix='landlaw-phase2c-') as folder:
        settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
            groq_api_key='', allow_stale_generation=False, sqlite_path=str(Path(folder)/'candidate.db'))
        runtime_fingerprint = configuration_fingerprint(settings)
        store = Store(settings)
        try:
            store.stage(payload)
            store.publish(payload['id'])  # Only this explicitly isolated SQLite.
            imported = [record_source_review(store, p) for p in sorted(args.receipts.glob('*.json'))]
            activate_source_gate(store, args.policy)
            release = store.release(None, True)
            historical = {r['id']: r for split in ('smoke','supplemental','natural')
                for line in (Path('data/evaluation')/(split+'.jsonl')).read_text().splitlines()
                if (r := json.loads(line))}
            sequence = cases['cases'] + [{**historical[i], 'expected_status': status,
                'fixture_claims': [], 'frozen_historical_control': True} for i,status in
                [('S01','answered'),('S02','clarification_needed'),('S03','answered'),
                 ('N07','clarification_needed'),('N08','insufficient_evidence')]]
            # Keep the historical source-quote fixture from Phase2B unchanged.
            chunk = store.chunk(historical['N01']['gold_chunk_ids'][0], release['id'])
            sequence.append({**historical['N01'], 'id':'N01-HISTORICAL-FIXTURE',
                'expected_status':'answered','fixture_claims':[{'text':chunk.text,'citation_ids':[chunk.id]}],
                'frozen_historical_control':True})
            # An unreviewed-current citation must be rejected even if the fake judge would approve.
            negative = next(r for r in sequence if r['id']=='C06-UNREVIEWED')
            doc = store.open_document('luat-dat-dai-2024', release['id'], 'Điều 104')
            negative = {**negative,'fixture_claims':[{'text':doc.chunks[0].text,
                                                     'citation_ids':[doc.chunks[0].id]}]}
            sequence = [negative if r['id']==negative['id'] else r for r in sequence]
            for case in sequence:
                provider = FixtureProvider(settings, encoder, case['fixture_claims'])
                capture, events = {}, []
                class RecordingAgent(Agent):
                    async def finish(self, state):
                        capture['contexts'] = self.context(state)
                        capture['synthesis_context'] = self.prompt_context(state)[0]
                        capture['draft'] = state['draft'].model_dump(mode='json')
                        capture['verifier'] = state['verification'].model_dump(mode='json')
                        capture['source_reviews'], capture['source_issues'] = await self.claim_source_reviews(state,state['draft'].claims)
                        return await super().finish(state)
                async def emit(event):events.append(event.model_dump(mode='json'))
                start = time.monotonic()
                row = {'id':case['id'],'question':case['question'],
                    'as_of':case.get('as_of',cases['as_of']), 'expected_status':case['expected_status'],
                    'kind':'deterministic_or_fixture_not_model', 'external_llm_requests':0,'external_llm_tokens':0}
                try:
                    result = await RecordingAgent(store, provider).run(ChatRequest(session_id='0'*36,
                        message=case['question'], as_of=date.fromisoformat(row['as_of']),
                        history=case.get('history',[])), emit)
                    row.update(answer=result.model_dump(mode='json'),
                        status_matches=result.status==case['expected_status'])
                    row['citation_integrity'] = all((c := store.chunk(cite.id,release['id'])) is not None
                        and cite.document_id==c.document_id and cite.excerpt==c.text
                        and cite.locator==c.locator for cite in result.citations)
                    required = case.get('required_articles',{})
                    row['required_article_evidence'] = {d+' / '+a: [c['citation_id'] for c in capture.get('contexts',[])
                        if c['document_id']==d and c['locator'].split(' · ')[0]==a]
                        for d, articles in required.items() for a in articles}
                    row['all_required_articles_retrieved'] = all(row['required_article_evidence'].values())
                    reviews = store.scoped_source_reviews(release,
                        [(c['document_id'], c['citation_id'], store.chunk(c['citation_id'], release['id']).checksum)
                         for c in capture.get('contexts',[])], date.fromisoformat(row['as_of']))
                    row['required_article_reviewed'] = {key:any(
                        reviews.get(key.split(' / ')[0]+':'+cid)=='fresh' for cid in ids)
                        for key,ids in row['required_article_evidence'].items()}
                    row['all_required_articles_reviewed'] = all(row['required_article_reviewed'].values())
                except Exception as exc:
                    row.update(error_type=type(exc).__name__,error=str(exc),status_matches=False)
                row.update(elapsed_ms=round((time.monotonic()-start)*1000),
                    fixture_generate_calls=provider.fixture_calls, fixture_outputs=provider.fixture_outputs,
                    events=events, **capture)
                records.append(row)
                with (args.output/'attempts.jsonl').open('a') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')
                print(json.dumps({'id':row['id'],'status':row.get('answer',{}).get('status'),
                    'matches':row['status_matches'],'required_articles':row.get('all_required_articles_retrieved'),
                    'error_type':row.get('error_type'),'issues':row.get('verifier',{}).get('issues',[])},ensure_ascii=False),flush=True)
            args.backup.parent.mkdir(parents=True,exist_ok=True)
            if args.backup.exists():raise ValueError('Backup output already exists')
            store.backup(args.backup)
            restored = Store(settings.model_copy(update={'sqlite_path':str(Path(folder)/'restore.db')}))
            try:
                restored.restore(args.backup)
                closed = not restored.source_gate_status(restored.release(None,True))['usable']
                for p in sorted(args.receipts.glob('*.json')):record_source_review(restored,p)
                exact = restored.release()['documents']==store.release()['documents']
                reopened = restored.source_gate_status(restored.release(None,True))['usable']
            finally:restored.close()
            report = {'checked_at':utcnow().isoformat(),'storage_backend':'isolated_sqlite',
                'corpus_id':payload['id'],'configuration_sha256':runtime_fingerprint,
                'runtime_unchanged':configuration_fingerprint(settings)==runtime_fingerprint,
                'source_gate':store.source_gate_status(release), 'whole_corpus_source_states':store.source_review_states(release),
                'external_llm_requests':0,'external_llm_tokens':0,
                'fixture_semantic_judge':True,'model_pass':None,
                'scope':'Real retrieval/structural verifier/source gate/citation rendering; draft and semantic judge are fixtures. Not model, PostgreSQL or public E2E acceptance.',
                'input_sha256':hashes,'inputs_unchanged':hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                'restore':{'exact_documents':exact,'missing_receipts_fail_closed':closed,'receipts_reapplied_usable':reopened},
                'backup':{'path':str(args.backup),'sha256':Encoder.file_sha(args.backup)},'receipts':imported,'cases':records}
            (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        finally:store.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','cases','policy','receipts','output','backup'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    def forbidden(*a,**k):raise AssertionError('External HTTP is forbidden in offline acceptance')
    async def async_forbidden(*a,**k):raise AssertionError('External HTTP is forbidden in offline acceptance')
    with patch.object(httpx.Client,'send',forbidden),patch.object(httpx.AsyncClient,'send',async_forbidden):
        asyncio.run(run(args))


if __name__=='__main__':main()
