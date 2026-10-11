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
