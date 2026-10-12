"""Operator-only immutable private archives with a conservative free-tier size limit."""
import hashlib

import httpx


class PrivateArchive:
    def __init__(self, settings):
        self.root = settings.supabase_url.rstrip('/') + '/storage/v1'
        self.bucket = settings.supabase_bucket
        key = settings.supabase_service_role_key.get_secret_value()
        if not settings.supabase_url or not key:
            raise ValueError('Supabase Storage credentials missing')
        self.client = httpx.AsyncClient(timeout=90, headers={'Authorization': 'Bearer '+key, 'apikey': key})

    async def close(self):
        await self.client.aclose()

    async def ensure_private(self):
        r = await self.client.get(f'{self.root}/bucket/{self.bucket}')
        if r.status_code == 404:
            r = await self.client.post(f'{self.root}/bucket', json={'id': self.bucket, 'name': self.bucket, 'public': False})
        if r.status_code not in (200, 201) or r.json().get('public') is not False:
            raise ValueError('Archive bucket must exist and be private')

    async def inventory(self):
        objects, prefixes = {}, ['']
        while prefixes:
            prefix = prefixes.pop()
            offset = 0
            while True:
                r = await self.client.post(f'{self.root}/object/list/{self.bucket}', json={'prefix': prefix, 'limit': 100, 'offset': offset})
                if r.status_code != 200:
                    raise ValueError('Cannot inspect archive usage')
                items = r.json()
                for item in items:
                    name = '/'.join(x for x in (prefix, item['name']) if x)
                    if item.get('id') is None:
                        prefixes.append(name)
                    else:
                        objects[name] = int((item.get('metadata') or {}).get('size', 0))
                if len(items) < 100:
                    break
                offset += 100
        return objects

    async def put(self, path, content, content_type='application/octet-stream'):
        r = await self.client.post(f'{self.root}/object/{self.bucket}/{path}', content=content,
                                   headers={'Content-Type': content_type, 'x-upsert': 'false'})
        if r.status_code in (200, 201):
            return 'created'
        # An existing immutable object is accepted only after its bytes are verified.
        if r.status_code in (400, 409):
            existing = await self.client.get(f'{self.root}/object/authenticated/{self.bucket}/{path}')
            if existing.status_code == 200 and hashlib.sha256(existing.content).digest() == hashlib.sha256(content).digest():
                return 'verified_existing'
        raise ValueError(f'Private archive upload failed or immutable object differs: HTTP {r.status_code}')

    async def upload_files(self, files):
        await self.ensure_private()
        inventory = await self.inventory()
        additional = sum(len(content) for path, content, _ in files if path not in inventory)
        if sum(inventory.values()) + additional > 700 * 1024 * 1024:
            raise ValueError('Archive would exceed the 700 MB reserve; prune reviewed releases first')
        results = []
        for path, content, content_type in files:
            results.append(await self.put(path, content, content_type))
        return {'objects': len(files), 'created': results.count('created'),
                'verified_existing': results.count('verified_existing'),
                'private': True, 'projected_bytes': sum(inventory.values()) + additional}
