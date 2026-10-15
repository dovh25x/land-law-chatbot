"""Run inside the exact deployment image under a hard 512 MB memory limit."""
import asyncio
import json
import resource

from landlaw.api import create_app
from landlaw.config import Settings
from landlaw.local_embedding import MODEL
from landlaw.provider import GroqProvider
from landlaw.store import Store
from landlaw.retrieval import HeadingIndex


async def main():
    settings=Settings(_env_file=None,sqlite_path='/tmp/memory-check.db',embedding_provider='local_onnx',
        embedding_model=MODEL['name'],embedding_dimensions=384,local_embedding_model_dir='/app/models/e5')
    store=Store(settings)
    provider=GroqProvider(settings,store)
    app=create_app(settings,store,provider)
    try:
        async with app.router.lifespan_context(app):
            # Exercise the new cache at the planned corpus size while the
            # encoder remains resident. These are memory fixtures, not law.
            rows=[{'id':f'memory-{i}','document_id':f'document-{i%80}',
                   'locator':f'Điều {i}',
                   'prefix':f'Điều {i}. Bồi thường tài sản và điều kiện hồ sơ 1. '+
                       ('Nội dung mẫu kiểm tra bộ nhớ, không làm căn cứ pháp luật. '*12)}
                  for i in range(8000)]
            heading_cache=HeadingIndex(rows)
            del rows
            assert heading_cache.rank('điều kiện bồi thường tài sản', {f'document-{i}' for i in range(80)})
            for _ in range(3):
                vectors=await asyncio.gather(*(provider.embed('Hà Nội bồi thường hỗ trợ tái định cư. '*120,query=True) for _ in range(2)))
                assert all(len(v)==384 for v in vectors)
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
        result={'passed':peak<450,'peak_rss_mib':peak,'limit_mib':512,'reserve_target_mib':62,
                'scope':'Exact Python 3.12 deployment image; FastAPI lifespan, resident 8,000-row heading cache and two concurrent long-query CPU embeddings; no LLM; memory fixtures do not certify law'}
        print(json.dumps(result))
        if not result['passed']:raise SystemExit('Insufficient memory reserve')
    finally:
        await provider.close()
        store.close()


asyncio.run(main())
