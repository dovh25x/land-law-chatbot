"""Reproduce a retrieved-only child citation across the two real agent versions.

All prose/decisions are explicit test doubles. This tests an integrity boundary,
never legal answer quality. HTTP is disabled and SQLite is disposable.
"""
import asyncio
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
from landlaw.agent import Agent
from landlaw.config import Settings
from landlaw.models import ChatRequest
from landlaw.provider import ProviderUnavailable
from landlaw.security import digest,utcnow
from landlaw.store import Store
from landlaw.embedding import contract

base=Path('reports/phase2d-synthesis-20261021')
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('landlaw.phase2d_before_guard',base/'baseline/backend/landlaw/agent.py')
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)

class Provider:
    configured=True
    def __init__(self,settings):self.settings=settings;self.shown=[]
    async def embed(self,*a,**k):raise ProviderUnavailable('Offline test embedding')
    async def generate(self,schema,instruction,payload,budget):
        budget.llm()
        if schema.__name__=='Plan':return schema(tools=[{'name':'search_law','query':payload['question']}])
        if schema.__name__=='Draft':
            self.shown.append(payload['evidence'])
            return schema(status='answered',claims=[{'text':'Điều kiện bồi thường phải được kiểm tra theo hồ sơ.',
                                                    'citation_ids':['law-child']}])
        return schema(supported_claim_indexes=[0],supporting_spans=[{'claim_index':i,'citation_id':cid,'span_id':s['span_id']}
            for i,c in enumerate(payload['draft']['claims']) for cid in c['citation_ids']
            for s in payload['source_spans'] if s['citation_id']==cid])

async def run():
    from landlaw.models import Chunk,Document
    text='Điều 1. Điều kiện bồi thường phải được kiểm tra theo hồ sơ.'
    child=Chunk(id='law-child',document_id='law',locator='Điều 1',text=text,checksum=digest(text),parent_id='law-parent')
    parent=child.model_copy(update={'id':'law-parent','parent_id':None,'text':text+' Điều kiện khác phải được đối chiếu đầy đủ.'})
    parent.checksum=digest(parent.text)
    doc=Document(id='law',title='Văn bản kiểm tra công khai',url='https://vanban.chinhphu.vn/?docid=1',
        source_kind='legal',checksum=digest('law'),checked_at=utcnow(),effective_from='2024-08-01',
        applicability_verified=True,chunks=[child,parent])
    with tempfile.TemporaryDirectory(prefix='landlaw-guard-repro-') as folder:
        settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',
            groq_api_key='',sqlite_path=str(Path(folder)/'test.db'))
        store=Store(settings)
        try:
            store.stage({'id':'test-only','checked_at':utcnow().isoformat(),'documents':[doc.model_dump(mode='json')],
                'relations':[],'embedding_model':settings.embedding_model,'embedding_dimensions':384,
                'embedding_contract':contract(settings)})
            store.publish('test-only')
            rows=[]
            for name,agent in [('before',old.Agent),('after',Agent)]:
                provider=Provider(settings)
                async def emit(event):pass
                answer=await agent(store,provider).run(ChatRequest(session_id='0'*36,message='Điều kiện bồi thường?'),emit)
                rows.append({'version':name,'status':answer.status,'citation_ids':[c.id for c in answer.citations],
                    'synthesis_payloads':provider.shown})
            value={'scope':'Synthetic integrity reproduction, not model/legal quality. Same SQLite and evidence.',
                   'external_llm_requests':0,'before_after':rows,
                   'regression_demonstrated':rows[0]['status']=='answered' and rows[0]['citation_ids']==['law-child']
                       and rows[1]['status']=='insufficient_evidence' and not rows[1]['citation_ids']}
            (base/'hidden-citation-reproduction-locked.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'regression_demonstrated':value['regression_demonstrated'],
                'before':rows[0]['status'],'after':rows[1]['status'],'external_llm_requests':0}))
        finally:store.close()

def forbid(*a,**k):raise AssertionError('No HTTP in this reproduction')
async def async_forbid(*a,**k):raise AssertionError('No HTTP in this reproduction')
with patch.object(httpx.Client,'send',forbid),patch.object(httpx.AsyncClient,'send',async_forbid):asyncio.run(run())
