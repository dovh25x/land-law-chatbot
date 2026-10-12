"""Allowed embedding contracts; generation and embedding credentials are independent."""
import re
import math
from datetime import datetime, timezone, timedelta

from .store import RateLimited


def workers_ai_retry_after(response):
    """Distinguish daily free allocation exhaustion from temporary capacity."""
    explicit=response.headers.get('retry-after')
    if explicit:
        try:return min(86400,max(1,math.ceil(float(explicit))))
        except (ValueError,TypeError):pass
    try:
        errors=response.json().get('errors',[])
        daily=any(item.get('code')==3036 for item in errors)
    except (ValueError,TypeError,AttributeError):daily=False
    if daily:
        now=datetime.now(timezone.utc)
        tomorrow=(now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
        return max(1,math.ceil((tomorrow-now).total_seconds()))
    return 60


def contract(settings, release=None):
    if release:
        value = release.get('embedding_contract') or {
            'provider': 'cloudflare' if release.get('embedding_model')=='@cf/baai/bge-m3' else 'gemini',
            'model': release.get('embedding_model','gemini-embedding-2'),
            'dimensions': release.get('embedding_dimensions',768), 'format_version':'v1'}
    else:
        value = {'provider':settings.embedding_provider,'model':settings.embedding_model,
                 'dimensions':settings.embedding_dimensions,'format_version':'v1'}
    allowed = {('gemini','gemini-embedding-2',768),('gemini','gemini-embedding-001',768),
               ('cloudflare','@cf/baai/bge-m3',1024)}
    if (value['provider'],value['model'],value['dimensions']) not in allowed or value.get('format_version')!='v1':
        raise ValueError('Unsupported embedding contract')
    return dict(value)


class CloudflareEmbeddings:
    def __init__(self,settings,client,record_usage,normalize):
        self.settings,self.client,self.record_usage,self.normalize=settings,client,record_usage,normalize

    async def embed_many(self,texts,title=None,query=False):
        from .provider import ProviderUnavailable
        account = self.settings.cloudflare_account_id
        token = self.settings.cloudflare_ai_api_token.get_secret_value()
        if not token or not re.fullmatch(r'[a-f0-9]{32}',account):
            raise ProviderUnavailable('Cloudflare Workers AI credentials missing')
        prepared = texts if query else [f'{title}\n{text}' if title else text for text in texts]
        await self.record_usage('cloudflare-embedding-requests')
        await self.record_usage('cloudflare-embedding-items',len(texts))
        try:
            response = await self.client.post(
                f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/baai/bge-m3',
                headers={'Authorization':'Bearer '+token}, json={'text':prepared})
        except Exception as exc:
            import httpx
            if isinstance(exc,httpx.HTTPError):
                raise ProviderUnavailable('Cloudflare embedding connection failed', retryable=True) from None
            raise
        if response.status_code==429:
            raise RateLimited(workers_ai_retry_after(response),source='provider')
        if response.status_code>=400:
            raise ProviderUnavailable(f'Cloudflare embedding HTTP {response.status_code}', retryable=response.status_code>=500)
        result=response.json()
        vectors=(result.get('result') or {}).get('data',[])
        if not result.get('success') or len(vectors)!=len(texts):
            raise ProviderUnavailable('Cloudflare embedding response shape mismatch')
        return [self.normalize(v,1024) for v in vectors]
