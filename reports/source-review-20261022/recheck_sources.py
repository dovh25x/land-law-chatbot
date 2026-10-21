"""Daily mechanical source re-verification for the pinned receipt set.

Re-fetches every official source artifact of the documents pinned by the
active source gate and compares content hashes (or extracted page text when
no hashable artifact is pinned) with the checksums recorded in the deployed
release corpus-1afca764aa6692e0. Never mutates a database or a receipt.
A real review verdict is only stamped later if every artifact matches.
"""
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RELEASE = json.loads((ROOT / 'data/staging/phase2c-current/release-v5.json').read_text())
BASE = Path(__file__).resolve().parent
OLD_TEXT = ROOT / 'reports/phase2c-current-20261021/source-text'

DOCS = ['luat-43-2024', 'luat-dat-dai-2024', 'luat-thu-do-2026', 'nd-151-2025',
        'nd-226-2025', 'nd-49-2026', 'nd-88-2024', 'nq-254-2025',
        'qd-10-2026-hanoi', 'qd-40-2026-hanoi']


def targets():
    docs = {d['id']: d for d in RELEASE['documents']}
    for item in DOCS:
        doc = docs[item]
        for index, file in enumerate(doc.get('source_files', [])):
            yield (item, f"{item}-file-{index}", file['url'], file['checksum'], 'bytes')
        for index, page in enumerate(doc.get('source_pages', [])):
            yield (item, f"{item}-page-{index}", page['url'], page['checksum'], 'bytes')
        if not doc.get('source_files') and not doc.get('source_pages'):
            # HTML article source without a pinned artifact: compare extracted text
            # with the byte-reviewed snapshot from the original reviewed pass.
            yield (item, f"{item}-html", doc['url'], None, 'text')


async def main():
    pending = list(targets())
    now = datetime.now(timezone.utc).isoformat()
    sem = asyncio.Semaphore(3)
    results = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36',
    }) as client:
        async def one(item, ident, url, expected, mode):
            async with sem:
                record = {'document_id': item, 'id': ident, 'url': url, 'checked_at': now,
                          'method': 'GET', 'expected_sha256': expected, 'mode': mode}
                try:
                    response = await client.get(url)
                    sha = hashlib.sha256(response.content).hexdigest()
                    record.update(status=response.status_code, sha256=sha, bytes=len(response.content))
                    if expected:
                        record['checksum_match'] = sha == expected
                    else:
                        text = BeautifulSoup(response.text, 'html.parser').get_text(' ', strip=True)
                        # Original reviewed snapshot was recorded under the document id.
                        snapshot_name = 'nd-88-2024.txt' if ident == 'nd-88-2024-html' else ident + '.txt'
                        snapshot = (OLD_TEXT / snapshot_name).read_text(encoding='utf-8')
                        record['text_match'] = text == snapshot
                        record['snapshot'] = str(OLD_TEXT / snapshot_name)
                except Exception as error:
                    record['error'] = type(error).__name__
                results.append(record)
        await asyncio.gather(*(one(*t) for t in pending))

    out = BASE / 'recheck-access.json'
    out.write_text(json.dumps(sorted(results, key=lambda r: (r['document_id'], r['id'])),
                              ensure_ascii=False, indent=2) + '\n')
    failures = [r for r in results if r.get('status') != 200
                or (r['mode'] == 'bytes' and not r.get('checksum_match'))
                or (r['mode'] == 'text' and not r.get('text_match'))]
    for r in sorted(results, key=lambda r: (r['document_id'], r['id'])):
        verdict = 'OK' if r not in failures else 'FAIL'
        detail = r.get('checksum_match', r.get('text_match'))
        print(verdict, r['document_id'], r['id'], r.get('status'), detail, r.get('error', ''))
    print('total:', len(results), 'failures:', len(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
