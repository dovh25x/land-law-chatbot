import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from landlaw.ingest import embed_pending
from landlaw.models import Chunk
from landlaw.provider import Budget, Gemini
from landlaw.security import digest
from landlaw.store import RateLimited
from landlaw.embedding import contract
from landlaw.publication import validate_demo


async def test_provider_does_not_enforce_legacy_daily_caps(settings, store):
    class Probe(BaseModel):
        ok: bool
    # Reproduce exhausted counters from the previous application configuration.
    store.consume([('llm:old-day', 100, 86400)])
    provider = Gemini(settings,store,httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,
        json={'candidates':[{'content':{'parts':[{'text':'{"ok":true}'}]}}]}))))
    for _ in range(105):
        assert (await provider.generate(Probe,'probe',{},Budget())).ok
    assert store.rows("SELECT value FROM counters WHERE key LIKE 'usage:llm:%'")[0]['value']==105
    await provider.close()


async def test_parallel_ingestion_keeps_successful_peer_checkpoint(tmp_path):
    class Provider:
        async def embed_many(self, texts, title=None):
            if texts[0]=='8':
                raise RateLimited(3600,source='provider')
            return [[1.0]+[0.0]*767 for _ in texts]
    pending = [(Chunk(id=str(n),document_id='doc',text=str(n),locator='Điều 1',checksum=digest(str(n))),
                tmp_path/f'{n}.json') for n in range(16)]
    issues=[]
    assert await embed_pending(Provider(),pending,'title',issues,'doc')
    assert sum(path.exists() for _,path in pending)==8
    assert issues[0]['quota_source']=='provider'
    assert json.loads((tmp_path/'0.json').read_text())['embedding'][0]==1


async def test_embedding_uses_release_contract_after_rollback(settings, store):
    seen=[]
    def handle(request):
        seen.append((str(request.url),json.loads(request.content)))
        if 'cloudflare' in str(request.url):
            return httpx.Response(200,json={'success':True,'result':{'data':[[1.0]+[0.0]*1023]}})
        return httpx.Response(200,json={'embedding':{'values':[1.0]+[0.0]*767}})
    configured=settings.model_copy(update={'embedding_provider':'cloudflare','embedding_model':'@cf/baai/bge-m3',
        'embedding_dimensions':1024,'cloudflare_account_id':'a'*32,'cloudflare_ai_api_token':settings.gemini_api_key})
    provider=Gemini(configured,store,httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    assert len(await provider.embed('bồi thường',query=True))==1024
    legacy={'embedding_model':'gemini-embedding-2','embedding_dimensions':768}
    assert len(await provider.embed('bồi thường',query=True,release=legacy))==768
    assert seen[0][1]['text']==['bồi thường']
    assert seen[1][1]['outputDimensionality']==768
    with pytest.raises(ValueError):
        contract(configured,{'embedding_contract':{'provider':'cloudflare','model':'@cf/baai/bge-m3','dimensions':768,'format_version':'v1'}})
    await provider.close()


def test_compressed_archive_restore_preserves_vectors_and_publication(settings, store, tmp_path):
    from conftest import document
    from landlaw.store import Store
    raw=document().model_dump(mode='json')
    raw['chunks'][0].update(embedding=[1.0]+[0.0]*1023,embedding_model='@cf/baai/bge-m3')
    payload={'id':'bge-release','documents':[raw],'checked_at':raw['checked_at'],'embedding_model':'@cf/baai/bge-m3','embedding_dimensions':1024}
    store.stage(payload)
    store.publish(payload['id'],{'profile':'demo','evidence_sha256':'review-hash'})
    assert store.rows('SELECT payload FROM releases')[0]['payload'].startswith('gzip:')
    archive=tmp_path/'backup.json'; store.backup(archive)
    recovered=Store(settings.model_copy(update={'sqlite_path':str(tmp_path/'restored.db')}))
    try:
        recovered.restore(archive)
        assert recovered.release()==payload
        assert len(recovered.chunk('law-1').embedding)==1024
        assert recovered.publication()['profile']=='demo'
        assert recovered.open_document('law',locator='Điều 1').chunks[0].text==raw['chunks'][0]['text']
        recovered.unpublish()
        assert recovered.release() is None
        assert recovered.release('bge-release')==payload
    finally: recovered.close()


def test_demo_gate_rejects_unreviewed_claims_and_wrong_release():
    raw={'id':'demo','embedded':True,'embedding_dimensions':1024,'documents':[{'checksum':'hash','checked_at':'today',
        'chunks':[{'embedding':[1.0]+[0.0]*1023}]}]}
    corpus={'coverage_passed':True,'verified_legal':31,'legal':31,'embedded':True}
    report={'release':'demo','configuration_sha256':'config','split':'smoke','cases':20,'completed_pairs':20,
        'source_audit_passed':True,'runtime_tests_passed':True,'source_audit_sha256':'audit','runtime_tests_sha256':'runtime','results':[{'mode':m,'reviewed':20,
            'answer_pass_rate':1,'citation_id_valid_rate':1,'critical_failed':[],'limited_or_error':0,
            'unsupported_claims':0,'source_review_complete':True,'claim_support_rate':1} for m in ('baseline','agentic')]}
    validate_demo(raw,corpus,report,'config')
    report['results'][0]['source_review_complete']=False
    with pytest.raises(ValueError): validate_demo(raw,corpus,report,'config')
    report['results'][0]['source_review_complete']=True
    report['release']='old'
    with pytest.raises(ValueError): validate_demo(raw,corpus,report,'config')


def test_extreme_table_padding_preserves_rows_and_units():
    from landlaw.ingest import chunks_for
    text='Đơn vị tính: nghìn đồng/m2\nSTT'+(' '*3000)+'Tên đường'+(' '*3000)+'Giá\n1'+(' '*3000)+'Đường A'+(' '*3000)+'12345\n2'+(' '*3000)+'Đường B'+(' '*3000)+'67890'
    chunks=chunks_for('prices',[(9,text)])
    assert all(len(c.text)<4000 and c.page==9 for c in chunks)
    assert '1   Đường A   12345' in chunks[0].text and '2   Đường B   67890' in chunks[0].text
    assert 'Đơn vị tính: nghìn đồng/m2' in chunks[0].text


def test_normalized_checkpoint_bytes_are_stable():
    vector=Gemini.normalize_vector([0.12345]*1024,1024)
    assert Gemini.normalize_vector(vector,1024)==vector


def test_retirement_requires_backup_and_preserves_published_releases(settings, store, tmp_path):
    from conftest import document
    from cryptography.fernet import Fernet
    from pydantic import SecretStr
    from landlaw.store import Store
    store.settings=settings.model_copy(update={'backup_encryption_key':SecretStr(Fernet.generate_key().decode())})
    for name in ('obsolete', 'live'):
        store.stage({'id':name,'documents':[document().model_dump(mode='json')]})
    store.publish('live')
    path=tmp_path/'retired.enc'
    with pytest.raises(ValueError): store.retire_staging(['live'],path)
    assert not path.exists()
    store.retire_staging(['obsolete'],path)
    assert store.release('obsolete') is None and store.release()['id']=='live'
    recovered=Store(store.settings.model_copy(update={'sqlite_path':str(tmp_path/'restored.db')}))
    try:
        recovered.restore(path)
        assert recovered.release('obsolete') and recovered.release()['id']=='live'
    finally: recovered.close()


def test_source_archive_includes_original_official_snapshots():
    from landlaw.cli import reviewed_source_files
    source={'raw_paths':['data/raw/normalized.html'],'raw_checksums':{'data/raw/normalized.html':'normalized'},
        'source_snapshot':{'raw_snapshots':[{'path':'data/raw/official.txt','sha256':'original'}]}}
    assert reviewed_source_files(source)==[('data/raw/normalized.html','normalized'),('data/raw/official.txt','original')]


def test_gemini_schema_simplification_keeps_local_tool_bounds():
    from landlaw.agent import SupportingQuote,ToolCall,Verification
    from landlaw.provider import generation_schema
    schema=generation_schema(Verification)
    assert 'maxItems' not in json.dumps(schema) and 'SupportingQuote' in schema['$defs']
    with pytest.raises(ValueError): ToolCall(name='search_law',query='x'*1001)
    with pytest.raises(ValueError): SupportingQuote(claim_index=10,citation_id='id',quote='source quote '*3)
