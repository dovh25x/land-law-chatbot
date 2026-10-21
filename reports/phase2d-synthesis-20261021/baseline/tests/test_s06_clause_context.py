"""Replay retained S06 evidence without a provider call or corpus mutation."""
import json
from datetime import date
from pathlib import Path

import pytest

from conftest import document, release
from test_agent import FakeProvider, noop
from landlaw.agent import Agent, Plan, Verification, model_passage_text, source_clause_spans
from landlaw.models import ChatRequest, Claim, Draft, Evidence
from landlaw.provider import Budget
from landlaw.security import digest


FIXTURE = json.loads(Path('tests/fixtures/s06-clause-attribution.json').read_text())


def s06_state(store):
    doc = document(document_number=FIXTURE['document_number'])
    doc.title = 'Luật Đất đai'
    doc.chunks = [doc.chunks[0].model_copy(update={
        'id': c['citation_id'], 'text': c['text'], 'locator': c['locator'],
        'page': c['page'], 'checksum': digest(c['text'])}) for c in FIXTURE['contexts']]
    payload = release(store, [doc])
    return {'request': ChatRequest(session_id='0'*36, message=FIXTURE['question']),
            'budget': Budget(), 'release': payload, 'as_of': date.fromisoformat(FIXTURE['as_of']),
            'plan': Plan(), 'history': [], 'tool_notes': [],
            'evidence': [Evidence(document=doc, chunk=c, applicability='current') for c in doc.chunks],
            'trace': [], 'emit': noop}


@pytest.mark.parametrize('article,owner,reference', [('95', '2', '1'), ('12', '3', '2'), ('7a', '4', '1')])
def test_clause_spans_distinguish_own_number_from_internal_cross_reference(article, owner, reference):
    raw = (f'Điều {article}. Điều kiện hỗ trợ. '
           f'{owner}. Các trường hợp quy định tại khoản {reference} Điều này có giấy xác nhận '
           'hoặc quyết định của cơ quan có thẩm quyền. a) Có giấy xác nhận; b) Có quyết định.')
    text = model_passage_text(raw)
    spans = source_clause_spans(text)
    assert [s['number'] for s in spans] == [owner]
    assert text[spans[0]['start']:spans[0]['end']].startswith(f'{owner}. Các trường hợp')
    assert ' '.join(text.split()) == raw
    assert f'Điều {article}.' in text


def test_continuation_is_not_assigned_to_the_clause_mentioned_inside_it():
    text = model_passage_text('b) Nhóm thuộc khoản 1 Điều 12; c) Điều kiện khác. '
                              '3. Chính phủ quy định trường hợp khác.')
    spans = source_clause_spans(text)
    assert [s['number'] for s in spans] == ['3']
    assert text[:spans[0]['start']].startswith('b) Nhóm thuộc khoản 1')
    assert source_clause_spans('Tham chiếu khoản 2 Điều 12, không có số khoản mở đầu.') == []


async def test_synthesis_receives_original_s06_conditions_with_explicit_clause_boundaries(store, settings):
    class CaptureProvider(FakeProvider):
        async def generate(self, schema, instruction, payload, budget):
            assert schema is Draft
            self.payload = payload
            budget.llm()
            return Draft(status='insufficient_evidence')

    state = s06_state(store)
    original = {c.chunk.id: c.chunk.text for c in state['evidence']}
    provider = CaptureProvider(settings)
    await Agent(store, provider).synthesize(state)
    contexts = provider.payload['evidence']
    assert len(contexts) == 3
    assert {' '.join(c['text'].split()) for c in contexts} == {' '.join(t.split()) for t in original.values()}
    conditions = next(c for c in contexts if '2. Các trường hợp' in c['text'])
    assert [s['number'] for s in conditions['clause_spans']] == ['2']
    span = conditions['clause_spans'][0]
    clause = conditions['text'][span['start']:span['end']]
    assert clause.startswith('2. Các trường hợp quy định tại khoản 1 Điều này')
    assert 'Giấy chứng nhận' in clause and 'quyết định giao đất' in clause
    dependency, = conditions['scope_dependencies']
    scope = next(c for c in contexts if any(s['number'] == '1' for s in c['clause_spans']))
    assert dependency['owner_clause'] == '2' and dependency['target_clause'] == '1'
    assert dependency['scope_citation_ids'] == [scope['citation_id']]
    assert len(json.dumps([contexts, provider.payload['documents']], ensure_ascii=False)) <= 7000
    assert all(c.chunk.text == original[c.chunk.id] for c in state['evidence'])


@pytest.mark.parametrize('draft_index', [0, 1])
async def test_both_retained_s06_wrong_clause_drafts_remain_unpublishable(store, settings, draft_index):
    state = s06_state(store)
    state['draft'] = Draft.model_validate(FIXTURE['rejected_drafts'][draft_index])
    state['verification'] = Verification(supported_claim_indexes=[0])
    agent = Agent(store, FakeProvider(settings))
    await agent.verify(state); await agent.finish(state)
    assert state['result'].status == 'insufficient_evidence'
    assert not state['result'].verified_claims and not state['result'].citations
    assert any('khoản 2' in issue or 'khoản 1' in issue for issue in state['verification'].issues)
    assert state['budget'].llm_calls == 0


@pytest.mark.parametrize('approved', [False, True])
async def test_correct_clause_and_actor_scope_still_requires_semantic_verifier_approval(store, settings, approved):
    state = s06_state(store)
    text = ('Đối với các trường hợp quy định tại khoản 1 Điều 95 Luật Đất đai 2024, '
            'khoản 2 Điều 95 quy định các điều kiện thay thế; giấy chứng nhận không phải điều kiện duy nhất, '
            'ngoài ra còn có quyết định giao đất hoặc quyết định cho thuê đất hoặc quyết định cho phép '
            'chuyển mục đích sử dụng đất của cơ quan nhà nước có thẩm quyền.')
    state['draft'] = Draft(status='answered', claims=[Claim(text=text, citation_ids=['C1', 'C3'])])
    verdict = (Verification(supported_claim_indexes=[0]) if approved else
               Verification(issues=['Claim 0: Nội dung chưa được chứng minh đầy đủ.']))
    agent = Agent(store, FakeProvider(settings, verification=verdict))
    await agent.verify(state)
    assert state['budget'].llm_calls == 1
    assert state['verification'].supported_claim_indexes == ([0] if approved else [])
    await agent.finish(state)
    assert state['result'].status == ('answered' if approved else 'insufficient_evidence')
    if approved:
        assert state['result'].verified_claims[0].text == text
        assert {c.id for c in state['result'].citations} == {'C1', 'C3'}
    else:
        assert not state['result'].verified_claims and not state['result'].citations
