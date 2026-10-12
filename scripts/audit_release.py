"""Recheck reviewed raw provenance and parsed content for one immutable release."""
import json
import sys
from pathlib import Path

from landlaw.config import Settings
from landlaw.ingest import coverage, json_write
from landlaw.security import digest, official_url, utcnow


def source_file_provenance(document, source, contents):
    """Reject attachment substitution and ambiguous page-to-file mappings."""
    files = document.get('source_files', [])
    known_urls = source.get('attachment_urls') or []
    if not known_urls and source['url'].split('?')[0].endswith('.pdf'):
        known_urls = [source['url']]
    expected = [(url, digest(raw)) for url, raw in zip(known_urls, contents, strict=True)
                if raw.startswith(b'%PDF')] if len(known_urls) == len(contents) else []
    if expected and [(f['url'], f['checksum']) for f in files] != expected:
        return False
    previous_end = -1
    for f in files:
        if (not official_url(f['url'], document.get('publication_url') or source['url'])
                or f['checksum'] not in source['raw_checksums'].values()
                or f['first_page_index'] <= previous_end
                or f['last_page_index'] < f['first_page_index']):
            return False
        previous_end = f['last_page_index']
    if files:
        prefix = document['id'] + '-'
        for chunk in document['chunks']:
            if chunk.get('page') is None:
                continue
            index = chunk['id'][len(prefix):].split('-', 1)[0] if chunk['id'].startswith(prefix) else ''
            if not index.isdigit() or sum(f['first_page_index'] <= int(index) <= f['last_page_index'] for f in files) != 1:
                return False
    return True


def main(path):
    settings = Settings()
    release = json.loads(Path(path).read_text())
    manifest = {s['id']:s for s in json.loads((settings.data_dir/'sources.json').read_text())}
    rows = []
    for document in release['documents']:
        source = manifest[document['id']]
        contents = [Path(p).read_bytes() for p in source['raw_paths']]
        snapshot=source.get('source_snapshot')
        artifacts=source.get('source_artifacts', [])
        sidecars=source.get('ocr_sidecars', [])
        checks = {
            'official_provenance':official_url(document['url'],document.get('publication_url')),
            'reviewed_raw':source.get('review_status')=='verified' and all(digest(b) in source['raw_checksums'].values() for b in contents),
            'document_checksum':digest(b''.join(contents))==document['checksum'],
            'chunk_checksums':all(digest(c['text'])==c['checksum'] for c in document['chunks']),
            'locators':all(c.get('locator') and c.get('text') for c in document['chunks']),
            'unique_chunks':len({c['id'] for c in document['chunks']})==len(document['chunks']),
            'personal_data_review':not source.get('contains_personal_data') or source.get('anonymisation_reviewed') is True,
            'checked_at':bool(document.get('checked_at')),
            'pdf_citation_provenance':source_file_provenance(document, source, contents),
            'source_artifacts':all(digest(Path(item['path']).read_bytes())==item['sha256'] for item in artifacts),
            'ocr_review':all(item.get('review_status')=='verified'
                and digest(Path(item['ocr_path']).read_bytes())==item['ocr_sha256']
                and item['pdf_sha256'] in source['raw_checksums'].values() for item in sidecars),
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
