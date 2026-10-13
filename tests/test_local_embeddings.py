import ast
import json
from pathlib import Path

import httpx
import pytest

from landlaw.embedding import contract
from landlaw.local_embedding import MODEL, Encoder
from landlaw.provider import Gemini


def test_colab_and_runtime_have_identical_model_and_encoder():
    def selected(path):
        tree=ast.parse(Path(path).read_text())
        nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in {'Encoder','vector_valid'}]
        return [ast.dump(node,include_attributes=False) for node in nodes]
    assert selected('backend/landlaw/local_embedding.py') == selected('scripts/offline_e5_colab.py')
    import importlib.util
    spec=importlib.util.spec_from_file_location('colab_contract',Path('scripts/offline_e5_colab.py'))
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    assert MODEL==worker.MODEL


async def test_local_queries_use_release_contract_and_do_not_call_remote_embedding(settings,store):
    provider=Gemini(settings,store,httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200,json={'embedding':{'values':[1.0]+[0.0]*767}}))))
    class FixtureLocal:
        def embed_many(self,texts,title,query):
            assert query
            return [[1.0]+[0.0]*383 for _ in texts]
    provider.local_embeddings=FixtureLocal()
    release={'embedding_contract':{'provider':'local_onnx','model':MODEL['name'],'dimensions':384,
                                   'format_version':'v1','local_model_spec':MODEL}}
    assert len(await provider.embed('bồi thường',query=True,release=release))==384
    assert len(await provider.embed('rollback',query=True,release={'embedding_model':'gemini-embedding-2','embedding_dimensions':768}))==768
    release['embedding_contract']['local_model_spec']={**MODEL,'query_max_tokens':512}
    with pytest.raises(ValueError,match='exact pinned'):
        contract(settings,release)
    await provider.close()


def test_metadata_cache_is_bounded_and_returns_independent_immutable_views(store):
    from conftest import release
    release(store)
    calls=[]
    original=store.rows
    def traced(sql,params=()):
        if 'FROM release_metadata' in sql:calls.append(params)
        return original(sql,params)
    store.rows=traced
    view=store.release('r1',metadata_only=True)
    view['documents'][0]['title']='Changed only in caller'
    assert store.document('law','r1').title!='Changed only in caller'
    assert len(calls)==1
    release(store,release_id='r2')
    release(store,release_id='r3')
    store.release('r2',metadata_only=True);store.release('r3',metadata_only=True)
    assert len(store._metadata_cache)==2


def test_unit_fixture_cannot_inherit_operator_database_or_provider_secrets(monkeypatch,tmp_path):
    from conftest import settings as fixture
    for name,value in {'DATABASE_URL':'postgresql://owner:private@invalid.example/database',
                       'ADMIN_DATABASE_URL':'postgresql://owner:private@invalid.example/database',
                       'LLM_PROVIDER':'groq','GROQ_API_KEY':'operator-private-key',
                       'EMBEDDING_PROVIDER':'local_onnx','EMBEDDING_MODEL':MODEL['name'],
                       'EMBEDDING_DIMENSIONS':'384','SUPABASE_SERVICE_ROLE_KEY':'operator-private-key'}.items():
        monkeypatch.setenv(name,value)
    isolated=fixture.__wrapped__(tmp_path)
    assert not isolated.database_url.get_secret_value() and not isolated.admin_database_url.get_secret_value()
    assert isolated.llm_provider=='gemini' and isolated.embedding_provider=='gemini'
    assert not isolated.groq_api_key.get_secret_value() and not isolated.supabase_service_role_key.get_secret_value()
