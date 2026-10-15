"""Academic publication status; never a legal certification."""
import math


def public_status(release, publication=None):
    return {'publication_profile':'academic' if release else 'staging',
            'quality_status':'academic_prototype',
            'retrieval_mode':'hybrid' if (release or {}).get('embedded') else 'unavailable',
            'coverage_gaps':(release or {}).get('coverage_gaps',[])}


def validate_corpus(release, corpus=None):
    from .security import official_url
    from .local_embedding import MODEL
    if not release.get('embedded') or not release.get('documents'):
        raise ValueError('Complete embedded corpus is required')
    from .embedding import contract
    contract(None,release)
    for doc in release['documents']:
        if not doc.get('checksum') or not doc.get('checked_at') or not doc.get('url') or not doc.get('chunks'):
            raise ValueError('Missing source provenance')
        if not official_url(doc['url'],doc.get('publication_url')):
            raise ValueError('Official source required')
        for chunk in doc['chunks']:
            vector=chunk.get('embedding') or []
            if len(vector)!=MODEL['dimensions'] or not all(type(x) in (int,float) and math.isfinite(x) for x in vector) or not any(vector):
                raise ValueError('Invalid embedding contract')
