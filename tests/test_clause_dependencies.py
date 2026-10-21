"""Dependency metadata comes only from explicit public source cross-references."""
from datetime import date

import pytest

from conftest import document, release
from test_agent import FakeProvider, noop
from landlaw.agent import Agent, Plan
from landlaw.models import ChatRequest, Draft, Evidence
from landlaw.provider import Budget
from landlaw.security import digest


@pytest.mark.parametrize('owner_article,owner_clause,target_article,target_clause', [
    ('12', '2', '12', '1'), ('7a', '4', '7a', '3'), ('18', '3', '6', '2'),
])
async def test_synthesis_explicitly_links_scope_and_condition_clauses(
        store, settings, owner_article, owner_clause, target_article, target_clause):
    reference = 'Điều này' if owner_article == target_article else f'Điều {target_article}'
    texts = [
        (f'Điều {target_article}', f'Điều {target_article}. Đối tượng. {target_clause}. Các trường hợp gồm người sử dụng đất hợp pháp.'),
        (f'Điều {owner_article}', f'Điều {owner_article}. Điều kiện. {owner_clause}. Các trường hợp quy định tại khoản '
         f'{target_clause} {reference} được hỗ trợ khi có một trong các điều kiện: a) Có giấy xác nhận; b) Có quyết định.'),
    ]
    doc = document()
    doc.chunks = [doc.chunks[0].model_copy(update={
        'id': f'law-{index}', 'locator': locator, 'text': text, 'checksum': digest(text)})
        for index, (locator, text) in enumerate(texts)]
    payload = release(store, [doc])
    state = {'request': ChatRequest(session_id='0'*36, message=f'Điều {owner_article} quy định điều kiện hỗ trợ thế nào?'),
             'release': payload, 'as_of': date(2024, 8, 2), 'budget': Budget(), 'plan': Plan(),
             'evidence': [Evidence(document=doc, chunk=c, applicability='current') for c in doc.chunks],
             'history': [], 'trace': [], 'emit': noop, 'tool_notes': []}

    class Capture(FakeProvider):
        async def generate(self, schema, instruction, context, budget):
            self.payload, self.instruction = context, instruction
            return Draft(status='insufficient_evidence')

    provider = Capture(settings)
    await Agent(store, provider).synthesize(state)
    contexts = provider.payload['evidence']
    source = next(c for c in contexts if f'{owner_clause}. Các trường hợp quy định' in c['text'])
    target = next(c for c in contexts if 'Đối tượng.' in c['text'])
    dependency, = source['scope_dependencies']
    assert dependency['owner_clause'] == owner_clause
    assert dependency['target_article'] == target_article
    assert dependency['target_clause'] == target_clause
    assert dependency['scope_citation_ids'] == [target['citation_id']]
    start, end = dependency['source_span']
    assert source['text'][start:end].startswith(f'{owner_clause}. Các trường hợp quy định tại khoản {target_clause}')
    assert 'scope_dependencies' in provider.instruction
    assert {c['citation_id'] for c in contexts} == set(provider.payload['allowed_citation_ids'])
    assert [(c.locator, c.text) for c in doc.chunks] == texts


def present(passages):
    from landlaw.agent import synthesis_passages
    return synthesis_passages(passages)


def passage(text, locator='Điều 12', citation_id='C1', document_id='law'):
    return {'text': text, 'locator': locator, 'citation_id': citation_id, 'document_id': document_id}


def test_unavailable_scope_is_explicit_not_invented_or_bound_to_a_different_document():
    text = '2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có giấy xác nhận.'
    contexts = present([passage(text), passage('1. Nhóm khác.', citation_id='C2', document_id='other')])
    dependency, = contexts[0]['scope_dependencies']
    assert dependency['target_clause'] == '1'
    assert dependency['target_article'] == '12'
    assert dependency['scope_citation_ids'] == []


@pytest.mark.parametrize('locator,text', [
    ('Điều 12', '3. Nội dung có dẫn khoản 1 Điều này nhưng không chứa khoản đó.'),
    ('Điều 12a', '1. Nhóm đối tượng của điều khác.'),
])
def test_internal_reference_or_similar_article_number_is_not_target_scope(locator, text):
    contexts = present([
        passage('2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có giấy xác nhận.'),
        passage(text, locator, 'C2'),
    ])
    assert contexts[0]['scope_dependencies'][0]['scope_citation_ids'] == []


@pytest.mark.parametrize('text', [
    'b) Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có giấy xác nhận.',
    '2. Tham khảo khoản 1 Điều này về thủ tục; không quy định đối tượng được hỗ trợ.',
    '2. Các điều kiện như giấy xác nhận theo khoản 1 Điều này.',
    '2. Các trường hợp quy định tại khoản 1 và khoản 3 Điều này được hỗ trợ.',
    '2. Các trường hợp quy định tại khoản 1 Điều 8 của Luật số 99/2024/QH15 được hỗ trợ.',
])
def test_non_scope_or_ambiguous_references_do_not_create_inferred_dependencies(text):
    assert not present([passage(text)])[0].get('scope_dependencies')


def test_explicit_article_reference_and_internal_cross_reference_are_separate():
    contexts = present([
        passage('4. Các đối tượng quy định tại Điều 6 của Luật này được hỗ trợ khi có giấy xác nhận.'),
        passage('Điều 6. Đối tượng gồm người đang sử dụng đất hợp pháp.', 'Điều 6', 'C2'),
    ])
    dependency, = contexts[0]['scope_dependencies']
    assert dependency['target_article'] == '6'
    assert dependency['target_clause'] is None
    assert dependency['scope_citation_ids'] == ['C2']


def test_dependency_points_to_same_passage_when_both_numbered_clauses_are_present():
    contexts = present([passage('Điều 12. Hỗ trợ. 1. Các trường hợp đủ điều kiện. '
                                '2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có giấy xác nhận.')])
    dependency, = contexts[0]['scope_dependencies']
    assert dependency['scope_citation_ids'] == ['C1']
    assert [span['number'] for span in contexts[0]['clause_spans']] == ['1', '2']
