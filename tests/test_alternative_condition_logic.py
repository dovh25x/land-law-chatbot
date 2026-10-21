"""Scope OR/AND checks to the required choice, without bypassing verification."""
from datetime import date

import pytest

from conftest import document, release
from test_agent import FakeProvider, noop
from landlaw.agent import Agent, Plan, Verification
from landlaw.models import ChatRequest, Claim, Draft, Evidence
from landlaw.provider import Budget


SOURCE = ('Điều 12. Điều kiện hỗ trợ. 1. Các trường hợp gồm người đang sử dụng đất hợp pháp. '
          '2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có một trong các điều kiện sau đây: '
          'a) Có giấy chứng nhận; b) Có quyết định giao đất.')
SCOPE = 'Các trường hợp thuộc khoản 1 Điều này '


def condition_state(store, text, source=SOURCE):
    doc = document(text=source)
    doc.chunks[0].locator = 'Điều 12'
    payload = release(store, [doc])
    return {'request': ChatRequest(session_id='0'*36, message='Điều kiện hỗ trợ theo Điều 12?'),
            'release': payload, 'as_of': date(2024, 8, 2), 'history': [], 'plan': Plan(),
            'draft': Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])]),
            'evidence': [Evidence(document=doc, chunk=doc.chunks[0], applicability='current')],
            'budget': Budget(), 'trace': [], 'emit': noop}


@pytest.mark.parametrize('text', [
    SCOPE + 'được hỗ trợ khi có một trong các điều kiện: giấy chứng nhận hoặc quyết định giao đất.',
    SCOPE + 'được hỗ trợ khi có giấy chứng nhận hoặc quyết định giao đất; không cần có cả hai giấy tờ.',
    SCOPE + 'được hỗ trợ còn phải có một trong các điều kiện: giấy chứng nhận hoặc quyết định giao đất.',
    SCOPE + 'được hỗ trợ còn phải có một trong các giấy tờ: giấy chứng nhận hoặc quyết định giao đất.',
    SCOPE + 'được hỗ trợ, đồng thời phải có một trong các điều kiện: giấy chứng nhận hoặc quyết định giao đất.',
    SCOPE + 'được hỗ trợ, đồng thời đáp ứng một trong các điều kiện: có giấy chứng nhận hoặc có quyết định giao đất.',
    'Ngoài việc thuộc đối tượng tại khoản 1 Điều này, người được hỗ trợ còn phải có một trong các điều kiện: '
    'giấy chứng nhận hoặc quyết định giao đất.',
    'Bên cạnh điều kiện về đối tượng thuộc khoản 1 Điều này, người được hỗ trợ còn phải có một trong các điều kiện: '
    'giấy chứng nhận hoặc quyết định giao đất.',
])
async def test_qualified_choice_reaches_semantic_verifier_without_becoming_cumulative(store, settings, text):
    state = condition_state(store, text)
    await Agent(store, FakeProvider(settings)).verify(state)
    assert state['budget'].llm_calls == 1
    assert state['verification'].supported_claim_indexes == [0]
    assert not state['verification'].issues
    assert state['draft'].claims[0].text == text


@pytest.mark.parametrize('requirement', [
    'ngoài giấy chứng nhận còn phải có quyết định giao đất.',
    'đồng thời phải có giấy chứng nhận và quyết định giao đất.',
    'đồng thời đáp ứng các điều kiện: có giấy chứng nhận và có quyết định giao đất.',
    'phải có tất cả các điều kiện: giấy chứng nhận và quyết định giao đất.',
    'phải có cả giấy chứng nhận và quyết định giao đất.',
    'phải đáp ứng đầy đủ các điều kiện: giấy chứng nhận và quyết định giao đất.',
    'phải có một trong các điều kiện; đồng thời phải có giấy chứng nhận và quyết định giao đất.',
    'còn phải có một trong các điều kiện; đồng thời đáp ứng các điều kiện: giấy chứng nhận và quyết định giao đất.',
    'còn phải có một trong các điều kiện và phải có cả giấy chứng nhận và quyết định giao đất.',
    'còn phải có một trong các điều kiện và phải có quyết định giao đất.',
    'còn phải có một trong các điều kiện; giấy chứng nhận vẫn bắt buộc.',
    'còn phải có một trong các điều kiện sau: có cả giấy chứng nhận và quyết định giao đất.',
    'ngoài giấy chứng nhận, người được hỗ trợ còn phải có một trong các điều kiện như quyết định giao đất.',
    'bên cạnh việc có giấy chứng nhận, người được hỗ trợ còn phải có một trong các điều kiện như quyết định giao đất.',
    'phải có giấy chứng nhận, đồng thời phải có một trong các điều kiện như quyết định giao đất.',
    'cần có giấy chứng nhận; còn phải có một trong các điều kiện như quyết định giao đất.',
    'còn phải có một trong các điều kiện; đồng thời phải có một trong các điều kiện khác.',
    'còn phải có một trong các điều kiện. Giấy chứng nhận vẫn bắt buộc; đồng thời phải có quyết định giao đất.',
    'không còn phải có một trong các điều kiện đã nêu.',
])
async def test_cumulative_or_negated_requirements_stay_blocked_even_if_model_would_approve(store, settings, requirement):
    state = condition_state(store, SCOPE + 'được hỗ trợ ' + requirement)
    agent = Agent(store, FakeProvider(settings))
    await agent.verify(state)
    assert state['budget'].llm_calls == 0
    assert not state['verification'].supported_claim_indexes
    assert any('đồng thời' in issue for issue in state['verification'].issues)
    await agent.finish(state)
    assert state['result'].status == 'insufficient_evidence'
    assert not state['result'].verified_claims and not state['result'].citations


@pytest.mark.parametrize('verdict', [
    Verification(issues=['Claim 0: Chưa chứng minh điều kiện này.']),
    Verification(supported_claim_indexes=[0], issues=['Claim 0: Sai phạm vi áp dụng.']),
])
async def test_or_phrase_never_bypasses_semantic_rejection(store, settings, verdict):
    state = condition_state(store, SCOPE + 'được hỗ trợ còn phải có một trong các điều kiện sau: '
                            'giấy chứng nhận hoặc quyết định giao đất.')
    agent = Agent(store, FakeProvider(settings, verification=verdict))
    await agent.verify(state)
    assert state['budget'].llm_calls == 1
    await agent.finish(state)
    assert not state['result'].verified_claims and not state['result'].citations


async def test_or_phrase_without_actor_dependency_remains_unpublishable(store, settings):
    state = condition_state(store, 'Để được hỗ trợ còn phải có một trong các điều kiện sau: '
                            'giấy chứng nhận hoặc quyết định giao đất.')
    agent = Agent(store, FakeProvider(settings))
    await agent.verify(state)
    assert state['budget'].llm_calls == 0
    assert any('đối tượng' in issue for issue in state['verification'].issues)
    await agent.finish(state)
    assert not state['result'].verified_claims and not state['result'].citations


async def test_source_that_actually_requires_and_is_not_rejected_as_or(store, settings):
    state = condition_state(store, SCOPE + 'được hỗ trợ đồng thời phải có giấy chứng nhận và quyết định giao đất.',
                            source=SOURCE.replace('một trong các điều kiện', 'đồng thời các điều kiện'))
    await Agent(store, FakeProvider(settings)).verify(state)
    assert state['budget'].llm_calls == 1
    assert state['verification'].supported_claim_indexes == [0]


async def test_correct_scoped_or_still_requires_exact_citation_proof(store, settings):
    class NoCitationProof(FakeProvider):
        async def generate(self, schema, instruction, payload, budget):
            budget.llm()
            return Verification(supported_claim_indexes=[0])

    state = condition_state(store, SCOPE + 'được hỗ trợ còn phải có một trong các điều kiện: '
                            'giấy chứng nhận hoặc quyết định giao đất.')
    agent = Agent(store, NoCitationProof(settings))
    await agent.verify(state)
    assert state['budget'].llm_calls == 1
    assert any('trích' in issue for issue in state['verification'].issues)
    await agent.finish(state)
    assert not state['result'].verified_claims and not state['result'].citations
