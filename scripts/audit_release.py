"""Recheck reviewed raw provenance and parsed content for one immutable release."""
import json
import sys
from pathlib import Path

from landlaw.config import Settings
from landlaw.ingest import coverage, json_write
from landlaw.security import digest, official_url, utcnow


def main(path):
    settings = Settings()
    release = json.loads(Path(path).read_text())
    manifest = {s['id']:s for s in json.loads((settings.data_dir/'sources.json').read_text())}
    rows = []
    for document in release['documents']:
        source = manifest[document['id']]
        contents = [Path(p).read_bytes() for p in source['raw_paths']]
        snapshot=source.get('source_snapshot')
        checks = {
            'official_provenance':official_url(document['url'],document.get('publication_url')),
            'reviewed_raw':source.get('review_status')=='verified' and all(digest(b) in source['raw_checksums'].values() for b in contents),
            'document_checksum':digest(b''.join(contents))==document['checksum'],
            'chunk_checksums':all(digest(c['text'])==c['checksum'] for c in document['chunks']),
            'locators':all(c.get('locator') and c.get('text') for c in document['chunks']),
            'unique_chunks':len({c['id'] for c in document['chunks']})==len(document['chunks']),
            'personal_data_review':not source.get('contains_personal_data') or source.get('anonymisation_reviewed') is True,
            'checked_at':bool(document.get('checked_at')),
            'snapshot_provenance':not snapshot or bool(official_url(snapshot.get('publication_url',''))
                and snapshot.get('retrieved_at') and snapshot.get('complete_lines')==391 and snapshot.get('overlap_matches')
                and snapshot.get('normalized_sha256')==document['checksum']
                and all(digest(Path(item['path']).read_bytes())==item['sha256'] for item in snapshot.get('raw_snapshots',[]))
                and len(snapshot.get('raw_snapshots',[]))==2),
        }
        rows.append({'id':document['id'],'checksum':document['checksum'],'chunks':len(document['chunks']),
                     'source_kind':document['source_kind'],'checks':checks,'passed':all(checks.values())})
    report={'release':release['id'],'checked_at':utcnow().isoformat(),'passed':all(r['passed'] for r in rows),
        'manifest_sha256':digest((settings.data_dir/'sources.json').read_bytes()),'documents':rows,
        'coverage':coverage(release),'coverage_gaps':release.get('coverage_gaps',[]),
        'scope':'Reviewed source provenance, checksums and parse structure. Legal claims reviewed separately in smoke; no independent legal certification.'}
    json_write(settings.reports_dir/'source-audit.json',report)
    print(json.dumps({'release':release['id'],'documents':len(rows),'passed':report['passed']}))
    if not report['passed']:
        raise SystemExit(1)


if __name__=='__main__': main(sys.argv[1])
