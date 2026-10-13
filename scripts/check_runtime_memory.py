"""Run inside the exact deployment image under a hard 512 MB memory limit."""
import asyncio
import json
import resource

from landlaw.api import create_app
from landlaw.config import Settings
from landlaw.local_embedding import MODEL
from landlaw.provider import Gemini
from landlaw.store import Store


async def main():
    settings=Settings(_env_file=None,sqlite_path='/tmp/memory-check.db',embedding_provider='local_onnx',
        embedding_model=MODEL['name'],embedding_dimensions=384,local_embedding_model_dir='/app/models/e5')
    store=Store(settings)
    provider=Gemini(settings,store)
    app=create_app(settings,store,provider)
    try:
        async with app.router.lifespan_context(app):
            for _ in range(3):
                vectors=await asyncio.gather(*(provider.embed('Hà Nội bồi thường hỗ trợ tái định cư. '*120,query=True) for _ in range(2)))
                assert all(len(v)==384 for v in vectors)
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
        result={'passed':peak<450,'peak_rss_mib':peak,'limit_mib':512,'reserve_target_mib':62,
                'scope':'Exact Python 3.12 deployment image; FastAPI lifespan and two concurrent long-query CPU embeddings; no LLM or legal fixture'}
        print(json.dumps(result))
        if not result['passed']:raise SystemExit('Insufficient memory reserve')
    finally:
        await provider.close()
        store.close()


asyncio.run(main())
