import httpx
import pytest
from pydantic import SecretStr

from landlaw.storage import PrivateArchive


def archive(settings, handler):
    item = PrivateArchive(settings.model_copy(update={'supabase_url':'https://test.supabase.co','supabase_service_role_key':SecretStr('private-test-key')}))
    item.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return item


async def test_public_archive_bucket_is_rejected(settings):
    item = archive(settings,lambda _:httpx.Response(200,json={'public':True}))
    try:
        with pytest.raises(ValueError,match='private'):
            await item.ensure_private()
    finally:
        await item.close()


async def test_immutable_archive_collision_requires_matching_bytes(settings):
    responses = [httpx.Response(400,json={'error':'Duplicate'}),httpx.Response(200,content=b'reviewed-source'),
                 httpx.Response(400,json={'error':'Duplicate'}),httpx.Response(200,content=b'changed-source')]
    item = archive(settings,lambda _:responses.pop(0))
    try:
        assert await item.put('raw/sha.pdf',b'reviewed-source') == 'verified_existing'
        with pytest.raises(ValueError,match='differs'):
            await item.put('raw/sha.pdf',b'reviewed-source')
    finally:
        await item.close()


async def test_multipart_corpus_restore_checks_every_part(settings, monkeypatch):
    import json
    release_id='corpus-1234567890abcdef'
    content=json.dumps({'id':release_id,'documents':[]}).encode()
    objects={}
    def handler(request):
        path=request.url.path
        if '/bucket/' in path:
            return httpx.Response(200,json={'public':False})
        if '/object/list/' in path:
            return httpx.Response(200,json=[])
        if request.method=='POST':
            objects[path.split('/object/legal-corpus/')[1]]=request.content
            return httpx.Response(200,json={})
        return httpx.Response(200,content=objects[path.split('/object/authenticated/legal-corpus/')[1]])
    item=archive(settings,handler)
    monkeypatch.setattr(item,'CORPUS_PART_BYTES',20)
    try:
        report=await item.upload_corpus(release_id,content)
        assert report['parts']>1 and await item.restore_corpus(release_id)==content
        path=next(p for p in objects if p.endswith('.gz.part'))
        objects[path]=b'tampered'
        with pytest.raises(ValueError,match='checksum or size'):
            await item.restore_corpus(release_id)
    finally:
        await item.close()
