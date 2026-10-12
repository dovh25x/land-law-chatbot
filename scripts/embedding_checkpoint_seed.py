"""Preserve real local embedding checkpoints in the private archive for CI resume."""
import asyncio
import gzip
import io
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key

from landlaw.config import Settings
from landlaw.ingest import json_write
from landlaw.provider import Gemini
from landlaw.security import digest
from landlaw.storage import PrivateArchive

MAX_BYTES = 180 * 1024 * 1024
MAX_COMPRESSED_BYTES = 60 * 1024 * 1024


def validate(items):
    if not isinstance(items, dict) or not items or len(items) > 20000:
        raise ValueError('Invalid checkpoint bundle')
    for name, checkpoint in items.items():
        if not re.fullmatch(r'[0-9a-f]{64}\.json', name) or set(checkpoint) != {'embedding'}:
            raise ValueError('Invalid checkpoint entry')
        Gemini.normalize_vector(checkpoint['embedding'],len(checkpoint['embedding']))
    return items


async def run(command):
    load_dotenv()
    settings = Settings()
    folder = settings.data_dir/'checkpoints'
    archive = PrivateArchive(settings)
    try:
        await archive.ensure_private()
        if command == 'archive':
            items = validate({p.name: json.loads(p.read_text()) for p in folder.glob('*.json')
                              if re.fullmatch(r'[0-9a-f]{64}\.json', p.name)})
            raw = json.dumps(items, sort_keys=True, separators=(',', ':')).encode()
            if len(raw) > MAX_BYTES:
                raise ValueError('Checkpoint seed exceeds the 180 MB expanded limit')
            # Small immutable shards fit Free Storage's per-object upload limit.
            files, shards = [], []
            entries = sorted(items.items())
            for offset in range(0,len(entries),800):
                part = gzip.compress(json.dumps(dict(entries[offset:offset+800]),sort_keys=True,separators=(',',':')).encode(),mtime=0)
                part_hash = digest(part)
                shards.append({'sha256':part_hash,'checkpoints':min(800,len(entries)-offset)})
                files.append((f'checkpoints/seeds/{part_hash}.json.gz',part,'application/gzip'))
            content = gzip.compress(json.dumps({'format':2,'shards':shards},sort_keys=True).encode(),mtime=0)
            checksum = digest(content)
            files.append((f'checkpoints/seeds/{checksum}.json.gz',content,'application/gzip'))
            report = await archive.upload_files(files)
            set_key('.env', 'EMBEDDING_SEED_SHA256', checksum)
            report.update({'checkpoints': len(items), 'seed_sha256': checksum,'format':2,'shards':len(shards)})
            json_write(settings.reports_dir/'embedding-seed.json', report)
            print(json.dumps(report))
        elif command == 'restore':
            checksum = os.getenv('EMBEDDING_SEED_SHA256', '')
            if not re.fullmatch(r'[0-9a-f]{64}', checksum):
                raise ValueError('Set EMBEDDING_SEED_SHA256 to the private seed checksum')
            r = await archive.client.get(f'{archive.root}/object/authenticated/{archive.bucket}/checkpoints/seeds/{checksum}.json.gz')
            if r.status_code != 200 or len(r.content) > MAX_COMPRESSED_BYTES or digest(r.content) != checksum:
                raise ValueError('Checkpoint seed unavailable or checksum differs')
            with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as stream:
                raw = stream.read(MAX_BYTES+1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Expanded checkpoint seed exceeds 180 MB')
            root = json.loads(raw)
            if root.get('format')==2:
                if not 1 <= len(root.get('shards',[])) <= 25:
                    raise ValueError('Invalid shard manifest')
                items = {}
                total_bytes=0
                for shard in root['shards']:
                    part_hash=shard['sha256']
                    if not re.fullmatch(r'[0-9a-f]{64}',part_hash):
                        raise ValueError('Invalid shard checksum')
                    part=await archive.client.get(f'{archive.root}/object/authenticated/{archive.bucket}/checkpoints/seeds/{part_hash}.json.gz')
                    if part.status_code!=200 or len(part.content)>MAX_COMPRESSED_BYTES or digest(part.content)!=part_hash:
                        raise ValueError('Checkpoint shard unavailable or checksum differs')
                    with gzip.GzipFile(fileobj=io.BytesIO(part.content)) as stream:
                        part_raw=stream.read(MAX_BYTES-total_bytes+1)
                    total_bytes+=len(part_raw)
                    if total_bytes>MAX_BYTES:
                        raise ValueError('Combined checkpoint shards exceed expanded limit')
                    entries=validate(json.loads(part_raw))
                    if set(items)&set(entries) or len(entries)!=shard['checkpoints']:
                        raise ValueError('Duplicate or incomplete checkpoint shard')
                    items.update(entries)
                items=validate(items)
            else:
                items = validate(root)
            folder.mkdir(parents=True, exist_ok=True)
            restored = 0
            for name, checkpoint in items.items():
                path = folder/name
                # Newer CI checkpoints win; seeds never overwrite cached results.
                if not path.exists():
                    path.write_text(json.dumps(checkpoint))
                    restored += 1
            print(json.dumps({'validated_checkpoints': len(items), 'restored': restored}))
        else:
            raise ValueError('Choose archive or restore')
    finally:
        await archive.close()


if __name__ == '__main__':
    asyncio.run(run(sys.argv[1]))
