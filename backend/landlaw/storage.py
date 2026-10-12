"""Operator-only immutable private archives with a conservative free-tier size limit."""
import hashlib
import gzip
import io
import json
import re

import httpx


class PrivateArchive:
    CORPUS_PART_BYTES = 20 * 1024 * 1024
    MAX_CORPUS_BYTES = 300 * 1024 * 1024
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

    async def upload_corpus(self, release_id, content):
        if not re.fullmatch(r'corpus-[0-9a-f]{16}', release_id) or len(content)>self.MAX_CORPUS_BYTES:
            raise ValueError('Invalid corpus archive identity or size')
        compressed=gzip.compress(content,mtime=0)
        files,parts=[],[]
        for offset in range(0,len(compressed),self.CORPUS_PART_BYTES):
            part=compressed[offset:offset+self.CORPUS_PART_BYTES]
            checksum=hashlib.sha256(part).hexdigest()
            path=f'{release_id}/parts/{checksum}.gz.part'
            parts.append({'path':path,'sha256':checksum,'bytes':len(part)})
            files.append((path,part,'application/octet-stream'))
        manifest={'format':1,'release':release_id,'sha256':hashlib.sha256(content).hexdigest(),
                  'bytes':len(content),'compressed_bytes':len(compressed),'parts':parts}
        files.append((f'{release_id}/corpus-manifest.json',json.dumps(manifest,sort_keys=True).encode(),'application/json'))
        report=await self.upload_files(files)
        return {**report,'release':release_id,'sha256':manifest['sha256'],'parts':len(parts)}

    async def restore_corpus(self, release_id):
        if not re.fullmatch(r'corpus-[0-9a-f]{16}',release_id):
            raise ValueError('Invalid corpus archive identity')
        await self.ensure_private()
        response=await self.client.get(f'{self.root}/object/authenticated/{self.bucket}/{release_id}/corpus-manifest.json')
        if response.status_code!=200 or len(response.content)>65536:
            raise ValueError('Corpus manifest unavailable')
        manifest=response.json()
        if (manifest.get('format')!=1 or manifest.get('release')!=release_id or
                not 0<manifest.get('bytes',0)<=self.MAX_CORPUS_BYTES or not 1<=len(manifest.get('parts',[]))<=20):
            raise ValueError('Invalid corpus archive manifest')
        parts=[]
        total=0
        for part in manifest['parts']:
            checksum=part.get('sha256','')
            if not re.fullmatch(r'[0-9a-f]{64}',checksum) or part.get('path')!=f'{release_id}/parts/{checksum}.gz.part':
                raise ValueError('Invalid corpus part path')
            r=await self.client.get(f"{self.root}/object/authenticated/{self.bucket}/{part['path']}")
            total+=len(r.content)
            if (r.status_code!=200 or len(r.content)>self.CORPUS_PART_BYTES or len(r.content)!=part.get('bytes') or
                    total>self.MAX_CORPUS_BYTES or hashlib.sha256(r.content).hexdigest()!=checksum):
                raise ValueError('Corpus part checksum or size differs')
            parts.append(r.content)
        if total!=manifest.get('compressed_bytes'):
            raise ValueError('Incomplete corpus archive')
        with gzip.GzipFile(fileobj=io.BytesIO(b''.join(parts))) as stream:
            content=stream.read(manifest['bytes']+1)
        if len(content)!=manifest['bytes'] or hashlib.sha256(content).hexdigest()!=manifest.get('sha256'):
            raise ValueError('Expanded corpus checksum or size differs')
        if json.loads(content).get('id')!=release_id:
            raise ValueError('Corpus identity differs')
        return content
