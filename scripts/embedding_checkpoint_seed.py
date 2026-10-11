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

MAX_BYTES = 30 * 1024 * 1024


def validate(items):
    if not isinstance(items, dict) or not items or len(items) > 20000:
        raise ValueError('Invalid checkpoint bundle')
    for name, checkpoint in items.items():
        if not re.fullmatch(r'[0-9a-f]{64}\.json', name) or set(checkpoint) != {'embedding'}:
            raise ValueError('Invalid checkpoint entry')
        Gemini.normalize_vector(checkpoint['embedding'])
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
                raise ValueError('Checkpoint seed exceeds 30 MB; archive a reviewed subset')
            content = gzip.compress(raw, mtime=0)
            checksum = digest(content)
            report = await archive.upload_files([(f'checkpoints/seeds/{checksum}.json.gz', content, 'application/gzip')])
            set_key('.env', 'EMBEDDING_SEED_SHA256', checksum)
            report.update({'checkpoints': len(items), 'seed_sha256': checksum})
            json_write(settings.reports_dir/'embedding-seed.json', report)
            print(json.dumps(report))
        elif command == 'restore':
            checksum = os.getenv('EMBEDDING_SEED_SHA256', '')
            if not re.fullmatch(r'[0-9a-f]{64}', checksum):
                raise ValueError('Set EMBEDDING_SEED_SHA256 to the private seed checksum')
            r = await archive.client.get(f'{archive.root}/object/authenticated/{archive.bucket}/checkpoints/seeds/{checksum}.json.gz')
            if r.status_code != 200 or len(r.content) > MAX_BYTES or digest(r.content) != checksum:
                raise ValueError('Checkpoint seed unavailable or checksum differs')
            with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as stream:
                raw = stream.read(MAX_BYTES+1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Expanded checkpoint seed exceeds 30 MB')
            items = validate(json.loads(raw))
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
