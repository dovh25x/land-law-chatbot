"""Public provenance for relevant sources not yet included in the answer index."""
import json
import re

from .security import official_url


def references(settings, indexed_ids):
    path = settings.data_dir / 'sources.json'
    if not path.exists():
        return []
    result = []
    for source in json.loads(path.read_text()):
        if (source['id'] in indexed_ids or not re.fullmatch(r'[a-z0-9-]+', source['id'])
                or source.get('project') not in (None, 'ring4')
                or source.get('source_kind') not in ('legal', 'project_decision', 'official_news','official_procedure','official_directory')
                or (source.get('source_kind') != 'legal' and source.get('project') != 'ring4')
                or (source.get('contains_personal_data') and not source.get('anonymisation_reviewed'))):
            continue
        url = source.get('publication_url') or source.get('metadata_url') or source['url']
        if not official_url(url):
            continue
        item = {key: source.get(key) for key in ('id', 'title', 'document_number', 'source_kind',
            'project', 'issued_on', 'effective_from', 'effective_to', 'checked_at')}
        item.update(url=url, availability='reference_only', applicability_verified=False,
            source_review_notes='Tài liệu gốc để đối chiếu. Nội dung chưa nằm trong chỉ mục trả lời; không dùng làm căn cứ cho kết luận AI.',
            attachment_urls=[link for link in source.get('attachment_urls', []) if official_url(link, url)],
            chunks=[])
        result.append(item)
    return result
