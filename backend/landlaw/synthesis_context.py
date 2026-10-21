"""Bounded, source-preserving synthesis packing. No retrieval or legal admission.

The caller supplies admitted candidates in relevance order. A projected passage
is an explicitly numbered source paragraph, never a summary or a clipped list.
Raw sources and citation locators remain immutable.
"""
import json
import re

from .security import normalize


CONTEXT_LIMIT = 7000
RELATION_FIELDS = ['source_id', 'target_id', 'type', 'source_locator',
                   'target_locators', 'target_locators_complete',
                   'source_effective_from', 'source_verified']


def article_key(item):
    return item['document_id'], item['locator'].split(' · ')[0]


def articles(locator):
    return set(re.findall(r'\bdieu\s+(\d+[a-z]?)\b', normalize(locator or '')))


def paragraph_view(item, question, format_text, clause_spans, required_clauses=()):
    """Offer complete numbered paragraphs plus their literal internal references.

    Only paragraphs with a source terminator are eligible. Never clip a point,
    infer the owner of an unnumbered prefix, or split inside quoted amendments.
    The full passage remains the fallback for ambiguous numbering/quotations.
    """
    text = format_text(item['text'])
    spans = clause_spans(text)
    if not spans:
        return item
    if any(text[:span['start']].count('“') != text[:span['start']].count('”') for span in spans):
        return item
    units = {s['number']: re.split(r'\s+Mục\s+\d+\s+[A-ZĐÀ-Ỹ][A-ZĐÀ-Ỹ,\s]{10,}$',
             text[s['start']:s['end']],maxsplit=1)[0].strip() for s in spans}
    if len(units) != len(spans):
        return item
    terms = set(normalize(question).split()) - {
        'cua', 'va', 'tai', 'cho', 'co', 'khong', 'theo', 'dieu', 'khoan', 'quy', 'dinh'}
    def score(number):
        words = set(normalize(units[number]).split())
        return len(words & terms) / max(1, len(words)) ** .5
    best = max(units, key=score)
    keep = set(required_clauses) & units.keys() or {best}
    while True:
        needed = {number for number in units if any(re.search(
            rf'\bkhoan\s+{re.escape(number)}\s+(?:va\s+khoan\s+\d+\s+)?dieu\s+nay\b',
            normalize(units[owner])) for owner in keep if '“' not in units[owner] and '"' not in units[owner])}
        if needed <= keep:
            break
        keep |= needed
    if any(not units[number].endswith(('.', ';', ':')) for number in keep):
        return item
    # A numbered paragraph can refer to its own document's other article. Its
    # scope is preserved in the text; absence of that source is handled below.
    prefix = text[:spans[0]['start']].strip()
    heading = prefix if re.match(r'^Điều\s+\d+', prefix) else ''
    if len(normalize(heading))<20:heading=''
    chosen=[s for s in spans if s['number'] in keep]
    parts=([heading] if heading else [])
    previous_end=spans[0]['start'] if heading else None
    for span in chosen:
        if parts and previous_end!=span['start']:
            parts.append('[…]')
        parts.append(units[span['number']])
        previous_end=span['end']
    projected = '\n'.join(parts)
    if len(projected) >= len(text):
        return item
    return {**item, 'text': projected}


def metadata_for(passages, candidates, compact=False):
    """Do not spend the source budget repeating the entire corpus graph.

    Keep effectivity exceptions for the supplied articles. Emit each relevant
    relation once; the full unmodified graph is still used by claim guards.
    """
    selected = {}
    for passage in passages:
        selected.setdefault(passage['document_id'], set()).update(articles(passage['locator']))
    docs, seen = {}, set()
    for item in candidates:
        doc_id = item['document_id']
        if doc_id not in selected or doc_id in docs:
            continue
        doc = {key: item[key] for key in ('document_id', 'title', 'document_number', 'kind',
               'effective_from', 'effective_to', 'source_review_notes')}
        doc['provision_validity'] = [scope for scope in item.get('provision_validity', [])
            if not articles(scope.get('locator')) or articles(scope['locator']) & selected[doc_id]]
        if item.get('operational_reviewed_at') or item['kind'] in {'official_procedure', 'official_directory'}:
            doc.update({key:item[key] for key in ('administrative_scope', 'procedure_id',
                'operational_reviewed_at', 'operational_review_status', 'required_dependency_ids')})
        rows = []
        for relation in item.get('legal_relations', []):
            source, target = relation['source_id'], relation['target_id']
            source_articles = articles(relation.get('source_locator'))
            target_articles = set().union(*(articles(loc) for loc in relation.get('target_locators', [])))
            if compact and source in selected and source_articles and not source_articles & selected[source]:
                continue
            if compact and target in selected and relation.get('target_locators_complete') and target_articles and not target_articles & selected[target]:
                continue
            # Missing incoming proof is diagnosed separately and still vetoed
            # by claim guards; document links are never substantive proof.
            if compact and (target not in selected or source not in selected):
                continue
            scoped = dict(relation)
            if compact and target_articles and target in selected:
                scoped['target_locators'] = [loc for loc in relation.get('target_locators', [])
                    if not articles(loc) or articles(loc) & selected[target]]
                if scoped['target_locators'] != relation.get('target_locators', []):
                    scoped['target_locators_complete'] = False
            row = [scoped.get(key) for key in RELATION_FIELDS]
            key = json.dumps(row, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                rows.append(row)
                seen.add(key)
        if rows:
            doc['legal_relation_fields'], doc['legal_relations'] = RELATION_FIELDS, rows
        doc={key:value for key,value in doc.items() if value not in (None,'',[], 'None') or key in {'document_id','kind'}}
        docs[doc_id] = doc
    result=list(docs.values())
    if compact:
        indices={doc['document_id']:i for i,doc in enumerate(result)}
        links=[]
        for doc in result:
            for row in doc.get('legal_relations',[]):
                source,target,kind=row[:3]
                link=[indices[source],indices[target],kind]
                if link not in links:links.append(link)
            doc.pop('legal_relations',None)
            doc.pop('legal_relation_fields',None)
            if doc.get('document_number'):doc.pop('title',None)
        if links:
            result[0]['legal_relation_fields']=['source_document_index_0based','target_document_index_0based','type']
            result[0]['legal_relations']=links
            result[0]['relation_scope']='source text'
    return result


def pack_context(candidates, question, present, format_text, clause_spans, as_of=None):
    """Coverage before repeated fragments, then whole-source budget admission."""
    compact=False
    def passage(item):
        fields=('citation_id','document_id','locator','text','applicability') if compact else (
            'citation_id','document_id','page','locator','text','applicability')
        return {key:item[key] for key in fields}

    def package(items):
        raw = [passage(item) for item in items]
        docs = metadata_for(raw, candidates, compact=compact)
        # Count the actual compact JSON and aliases sent by GroqProvider,
        # including paragraph/dependency metadata. The cap itself is unchanged.
        wire=[{**item,'citation_id':f'C{index+1}'} for index,item in enumerate(raw)]
        size = len(json.dumps([present(wire), docs], ensure_ascii=False,separators=(',',':')))
        return raw, docs, size

    # With ample room preserve original parent/continuation selection exactly.
    raw, docs, size = package(candidates)
    if size <= CONTEXT_LIMIT:
        return raw, docs, {item['citation_id']:'included_whole' for item in candidates}

    compact=True

    # Close a ranked article over reviewed source relations before unrelated
    # similarity hits. Scope is matched to article locators, never act numbers.
    groups = {}
    for item in candidates:
        groups.setdefault(article_key(item), []).append(item)
    relations = {json.dumps(r,sort_keys=True):r for item in candidates
                 for r in item.get('legal_relations', [])}
    ordered_keys, hints = [], {}
    def links(key, kinds, outgoing=False):
        result=[]
        for relation in relations.values():
            if relation['type'] not in kinds:
                continue
            starts=relation.get('source_effective_from')
            if starts and as_of and starts>str(as_of):
                continue
            source,target=relation['source_id'],relation['target_id']
            if outgoing:
                scope=articles(relation.get('source_locator'))
                if source!=key[0] or not scope or not scope & articles(key[1]):
                    continue
                related=target
                locators=relation.get('target_locators',[])
            else:
                scope=set().union(*(articles(loc) for loc in relation.get('target_locators',[])))
                if target!=key[0] or (relation.get('target_locators_complete') and scope and not scope & articles(key[1])):
                    continue
                related=source
                locators=[relation.get('source_locator') or '']
            scopes=set().union(*(articles(loc) for loc in locators))
            for other in groups:
                if other[0]==related and (not scopes or articles(other[1]) & scopes):
                    clauses={number for loc in locators for number in re.findall(r'\bkhoan\s+(\d+)\b',normalize(loc))}
                    hints.setdefault(other,set()).update(clauses)
                    if other not in result:result.append(other)
        return result
    pending=[next(iter(groups))] if groups else []
    while pending:
        key=pending.pop(0)
        if key in ordered_keys:continue
        ordered_keys.append(key)
        # Direct amendment/repeal proof takes priority over deeper optional
        # cross-references. Breadth keeps a single act's graph from taking all
        # slots before the other governing acts are represented.
        immediate=links(key,{'amends','repeals'})
        later=links(key,{'guides'},outgoing=True)+links(key,{'overrides','transition'})
        pending=[other for other in immediate if other not in ordered_keys]+pending
        pending.extend(other for other in later if other not in ordered_keys and other not in pending)
    root_doc=next(iter(groups))[0] if groups else None
    leftovers=sorted(groups,key=lambda key:key[0]!=root_doc)
    ordered_keys.extend(key for key in leftovers if key not in ordered_keys)
    ordered=[item for key in ordered_keys for item in groups[key]]
    selected, reasons = [], {}
    for original in ordered:
        item=paragraph_view(original,question,format_text,clause_spans,hints.get(article_key(original),()))
        whole = package(selected + [item])
        if whole[2] <= CONTEXT_LIMIT:
            selected.append(item)
            reasons[item['citation_id']] = ('included_whole' if item['text']==original['text'] else 'included_numbered_paragraphs')
            continue
        reasons[item['citation_id']] = 'context_budget'
    raw, docs, size = package(selected)
    return raw, docs, reasons
