"""Real baseline retrieval diagnostic. No generation, answer scoring or publication."""
import asyncio
import json
import time
from pathlib import Path

from landlaw.agent import Agent
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, dataset, validate_frozen_benchmark
from landlaw.models import ChatRequest
from landlaw.provider import Budget, Gemini
from landlaw.security import local_date, utcnow
from landlaw.store import Store


async def main():
    settings=Settings()
    store=Store(settings)
    provider=Gemini(settings,store)
    release_id='corpus-de584c31fc95f9a2'
    records=[]
    configuration=configuration_fingerprint(settings)
    async def emit(_):pass
    try:
        release=store.release(release_id,metadata_only=True)
        source_check=validate_frozen_benchmark(settings.data_dir/'evaluation/questions.jsonl',
            settings.data_dir/'evaluation/acceptance-freeze.json',settings.data_dir/'evaluation/gold-sources.json',
            store,release_id)
        agent=Agent(store,provider)
        cases=[c for c in dataset(settings.data_dir/'evaluation/questions.jsonl') if c['split']=='acceptance']
        for case in cases:
            started=time.monotonic()
            request=ChatRequest(session_id='00000000-0000-0000-0000-000000000000',message=case['question'],
                mode='baseline',project=case.get('project'),as_of=case.get('as_of') or local_date())
            state={'request':request,'release':release,'as_of':request.as_of,'budget':Budget(),
                'history':case.get('history',[]),'trace':[],'emit':emit,'evidence':[],'rounds':0,'tool_notes':[]}
            await agent.plan(state)
            await agent.tools(state)
            hits=[item.chunk.id for item in state['evidence'][:8]]
            gold=set(case.get('gold_chunk_ids',[]))
            record={'case_id':case['id'],'gold_chunk_ids':sorted(gold),'retrieved_chunk_ids':hits,
                'recall_at_8':len(gold & set(hits))/len(gold) if gold else None,
                'seconds':round(time.monotonic()-started,3),'embedding_calls':state['budget'].embedding_calls,
                'llm_calls':state['budget'].llm_calls,'degraded':state.get('retrieval_degraded',False)}
            records.append(record)
            recalls=[r['recall_at_8'] for r in records if r['recall_at_8'] is not None]
            report={'checked_at':utcnow().isoformat(),'release':release_id,
                'configuration_sha256':configuration,'completed':len(records),'total':len(cases),
                'source_changed_during_run':configuration_fingerprint(settings)!=configuration,
                'mean_recall_at_8':sum(recalls)/len(recalls) if recalls else None,'source_validation':source_check,
                'scope':'Baseline retrieval-only diagnostic on frozen acceptance questions; no answer generation, no agentic score, no legal acceptance certification. No sessions or publication pointers written.',
                'records':records}
            settings.reports_dir.joinpath('retrieval-diagnostic.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(json.dumps({'case':case['id'],'recall':record['recall_at_8'],'completed':len(records)}),flush=True)
    finally:
        await provider.close()
        store.close()


if __name__=='__main__':asyncio.run(main())
