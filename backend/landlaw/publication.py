"""Separate an explicitly preliminary demo from full legal acceptance."""
import math


def public_status(release, publication=None):
    publication = publication or {}
    return {
        'publication_profile': publication.get('profile', 'staging'),
        'quality_status': 'accepted' if publication.get('profile') == 'accepted' else 'acceptance_pending',
        'retrieval_mode': 'hybrid' if (release or {}).get('embedded') else 'unavailable',
        'coverage_gaps': (release or {}).get('coverage_gaps', []),
    }


def validate_corpus(release, corpus):
    """Every publication profile needs complete, verified source/vector data."""
    if not corpus['coverage_passed'] or corpus['verified_legal'] != corpus['legal'] or not corpus['embedded']:
        raise ValueError('Demo requires verified source coverage and complete embeddings')
    dimension = release.get('embedding_dimensions', 768)
    for document in release['documents']:
        if not document.get('checksum') or not document.get('checked_at'):
            raise ValueError('Missing source provenance')
        for chunk in document['chunks']:
            vector = chunk.get('embedding') or []
            if len(vector) != dimension or not all(math.isfinite(x) for x in vector) or not any(vector):
                raise ValueError('Invalid embedding contract')


def validate_demo(release, corpus, report, configuration):
    """Missing mandatory history is disclosed; incomplete vectors never pass."""
    validate_corpus(release, corpus)
    if report.get('release') != release['id'] or report.get('configuration_sha256') != configuration:
        raise ValueError('Smoke evidence must match this release and configuration')
    if report.get('split') != 'smoke' or report.get('cases') != 20 or report.get('completed_pairs') != 20:
        raise ValueError('Twenty paired source-checked smoke cases are required')
    if not report.get('source_audit_passed') or not report.get('runtime_tests_passed'):
        raise ValueError('Source audit and runtime test evidence are required')
    if not report.get('source_audit_sha256') or not report.get('runtime_tests_sha256'):
        raise ValueError('Evidence artifacts must have checksums')
    for result in report.get('results', []):
        if (result.get('reviewed') != 20 or result.get('answer_pass_rate') != 1
                or result.get('citation_id_valid_rate') != 1 or result.get('critical_failed')
                or result.get('limited_or_error') or result.get('unsupported_claims') != 0
                or not result.get('source_review_complete') or result.get('claim_support_rate') != 1):
            raise ValueError('Every smoke result must pass reviewed grounding and behavior checks')
    if {r.get('mode') for r in report.get('results', [])} != {'baseline', 'agentic'}:
        raise ValueError('Smoke must review both modes')


def validate_technical_demo(release, corpus, report, configuration):
    """User-authorized technical demo, explicitly short of legal acceptance.

    The complete smoke/acceptance gates remain unchanged. Require real paired
    examples of temporal lookup, substantive law and private-file clarification
    with source reviews, plus technical and corpus evidence on this configuration.
    """
    validate_corpus(release, corpus)
    if (report.get('release')!=release['id'] or report.get('configuration_sha256')!=configuration
            or report.get('split')!='smoke' or report.get('cases')!=20):
        raise ValueError('Technical demo requires the unchanged smoke suite on this release/configuration')
    if not all(report.get(key) for key in ('source_audit_passed','runtime_tests_passed',
            'source_audit_sha256','runtime_tests_sha256')):
        raise ValueError('Technical demo requires source audit and runtime evidence')
    required={(case,mode) for case in ('S01','S07','S09') for mode in ('baseline','agentic')}
    reviewed=report.get('source_reviewed_results',[])
    passed={(row.get('case_id'),row.get('mode')) for row in reviewed
        if row.get('passed') and row.get('source_checked') and row.get('review_complete')
        and row.get('citation_ids_valid') and row.get('unsupported_claims')==0
        and row.get('status') not in {'limited','error'}}
    if not required<=passed:
        raise ValueError('Six source-reviewed temporal, substantive and private-file examples are required')
    if any(row.get('critical') and (not row.get('passed') or row.get('unsupported_claims')) for row in reviewed):
        raise ValueError('Resolve reviewed critical failures before technical demo publication')
