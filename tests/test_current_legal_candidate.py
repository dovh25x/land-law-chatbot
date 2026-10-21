"""Provision boundary/provenance regression; no model or production database."""
import copy
import json
from pathlib import Path

import pytest

from landlaw.agent import citation_source_url
from landlaw.models import Document, Evidence
from landlaw.security import digest
from scripts.prepare_current_legal_candidate import prepare, provision_excerpts


@pytest.fixture
def source():
    return json.loads(Path('tests/fixtures/current-source-provisions.json').read_text())


def test_scope_extracts_complete_clause_without_changed_neighbor(source):
    excerpts, _ = provision_excerpts(source)
    clause = excerpts[0]
    assert clause['text'].startswith('4. Hộ gia đình, cá nhân có đất ở')
    assert 'Điều 95' in clause['text']
    assert 'nhiều thế hệ' in clause['text']
    assert clause['text'].endswith('cho các hộ gia đình còn thiếu.')
    assert '3. Giá đất' not in clause['text']
    assert '5. Hộ gia đình' not in clause['text']


def test_amending_actor_scope_and_member_rule_are_separate(source):
    excerpts, _ = provision_excerpts(source)
    member, geography = excerpts[1:3]
    assert member['locator'] == 'Điều 2'
    assert member['text'].startswith('4. Bổ sung điểm d vào khoản 1 Điều 19')
    assert 'chung quyền sử dụng đất' in member['text']
    assert 'thời điểm phê duyệt phương án' in member['text']
    assert 'tự thỏa thuận và chịu trách nhiệm trước pháp luật' in member['text']
    assert '5. Bổ sung khoản 5' not in member['text']
    assert geography['locator'] == 'Điều 7'
    assert 'điểm a, điểm b khoản 2 Điều 11' in geography['text']
    assert 'cấp xã nơi có đất thu hồi' in geography['text']
    assert 'tại Nghị định số 101' not in geography['text']
    assert 'b) Bãi bỏ cụm từ' not in geography['text']
    assert 'Mẫu quyết định' not in geography['text']
    assert 'Mẫu số 44' not in geography['text']


def test_every_word_is_bound_to_source_slices_and_checksums(source):
    originals = {c['id']: c for d in source['documents'] for c in d['chunks']}
    excerpts, provenance = provision_excerpts(source)
    for excerpt, proof in zip(excerpts, provenance, strict=True):
        expected = []
        for part in proof['source_segments']:
            original = originals[part['chunk_id']]
            text = original['text'][part['start']:part['end']].strip()
            assert original['checksum'] == part['source_checksum']
            assert digest(text) == part['slice_sha256']
            expected.append(text)
        assert excerpt['text'] == '\n'.join(expected)
        assert digest(excerpt['text']) == excerpt['checksum'] == proof['text_sha256']


def test_only_four_local_vectors_added_and_base_is_immutable(source):
    before = copy.deepcopy(source)
    class Encoder:
        calls = []
        def encode(self, text, query=False):
            self.calls.append((text, query))
            return [1.0]+[0.0]*383
    encoder = Encoder()
    candidate, _ = prepare(source, encoder)
    assert source == before
    assert candidate['id'] != source['id']
    assert len(encoder.calls) == 4 and not any(q for _,q in encoder.calls)
    assert all(text.startswith(('Luật Đất đai\n','Sửa đổi')) or '\n' in text for text,_ in encoder.calls)
    for old, new in zip(source['documents'], candidate['documents'], strict=True):
        assert old['chunks'] == new['chunks'][:len(old['chunks'])]
        assert old['checksum'] == new['checksum']
    assert prepare(source, Encoder())[0]['id'] == candidate['id']
    with pytest.raises(ValueError, match='already exists'):
        provision_excerpts(candidate)


def test_excerpts_resolve_to_exact_attachment_and_physical_page(source):
    excerpts, _ = provision_excerpts(source)
    docs = {d['id']: Document.model_validate(d) for d in source['documents']}
    from landlaw.models import Chunk
    for raw, expected_page in zip(excerpts, [18,16,35,24], strict=True):
        doc = docs[raw['document_id']]
        item = Evidence(document=doc, chunk=Chunk.model_validate(raw), applicability='current')
        url = citation_source_url(item)
        assert url and url.endswith('#page='+str(expected_page))
        if doc.id == 'luat-dat-dai-2024':
            assert url.split('#')[0].endswith('31-2024-qh15_2.pdf')
        else:
            assert url.split('#')[0] == str(doc.source_files[0].url)


@pytest.mark.parametrize('question', [
    'Hộ có giấy chứng nhận, chưa có phương án được duyệt trước các mốc chuyển tiếp. Cần đối chiếu điều kiện bồi thường, không xác nhận quyền lợi hộ cụ thể.',
    'Hộ đủ điều kiện bồi thường, thu hồi đất trong cùng xã, không phải di chuyển chỗ ở: hỗ trợ ổn định đời sống thế nào?',
    'Chuyển nhà sau thu hồi đất, chưa xác định chính sách của dự án mới.',
    'Xác nhận điều kiện bồi thường trong phương án của hộ gia đình.',
])
def test_legal_questions_do_not_match_administrative_substrings(question):
    from landlaw.agent import place_mapping_question
    assert not place_mapping_question(question)


@pytest.mark.parametrize('question', [
    'Huyện Đan Phượng cũ nay thuộc xã mới nào?',
    'Địa bàn huyện cũ đã đổi thành xã nào?',
    'Tên huyện cũ và xã mới có ánh xạ ra sao?',
])
def test_actual_old_district_mapping_requests_still_match(question):
    from landlaw.agent import place_mapping_question
    assert place_mapping_question(question)


def test_guidance_scope_keeps_only_the_retrieved_source_article():
    from conftest import document
    from landlaw.models import Chunk, Relation
    from landlaw.agent import relation_may_affect
    doc = document('local-rule')
    relation = Relation(source_id=doc.id, target_id='national-rule', type='guides',
        source_locator='Điều 21', target_locators=['Khoản 4 Điều 111'],
        target_locators_complete=True, source_url=str(doc.url), explanation='Reviewed statutory cross-reference.')
    def passage(ident, article):
        d = document(ident)
        c = d.chunks[0].model_copy(update={'locator':f'Điều {article}'})
        return Evidence(document=d, chunk=c, applicability='current')
    assert relation_may_affect(relation, doc.id, [passage(doc.id,21)])
    assert not relation_may_affect(relation, doc.id, [passage(doc.id,17)])
    assert relation_may_affect(relation, 'national-rule', [passage('national-rule',111)])
    assert relation_may_affect(relation, 'national-rule', [passage('national-rule',108)])
    # Unknown target scope remains conservative, never interpreted as a proven absence.
    assert relation_may_affect(relation.model_copy(update={'target_locators_complete':False}),
                              'national-rule', [passage('national-rule',108)])


def test_reviewed_candidates_do_not_get_crowded_out_by_stale_hits(store, tmp_path):
    from conftest import document, release
    from test_scoped_source_gate import install_gate
    from landlaw.security import local_date
    good = document('reviewed', text='Điều 1. Điều kiện bồi thường về đất.')
    old = document('stale', text='Điều 1. Điều kiện bồi thường về đất. Điều kiện bồi thường về đất. Điều kiện bồi thường về đất.')
    payload = release(store, [old,good])
    query = 'điều kiện bồi thường về đất'
    assert store.search(query, as_of=local_date())[0].document.id == old.id
    install_gate(store, payload, good, tmp_path)
    hits = store.search(query, as_of=local_date())
    assert hits[0].document.id == good.id
    assert any(e.document.id == old.id for e in hits)  # Candidate generation is retained.
    reviews = store.scoped_source_reviews(payload,
        [(e.document.id,e.chunk.id,e.chunk.checksum) for e in hits], local_date())
    assert reviews[good.id+':'+good.chunks[0].id] == 'fresh'
    assert reviews[old.id+':'+old.chunks[0].id] != 'fresh'


@pytest.mark.parametrize('question,number,expected', [
    ('Đủ điều kiện tại Điều 5 của luật chung; Điều 17 Quy định kèm Quyết định 123/2026/QĐ-UBND quy định thế nào?', '123/2026/QĐ-UBND', '17'),
    ('Điều 7 của luật chung có điều kiện khác. Xin giải thích Điều 22 Nghị định 456/2025/NĐ-CP.', '456/2025/NĐ-CP', '22'),
    ('Điều 8 của Luật mẫu quy định thế nào?', '789/2024/QH15', '8'),
])
def test_article_binds_to_its_own_named_document(question, number, expected):
    from landlaw.agent import article_reference_for_document
    assert article_reference_for_document(question, number)[1] == expected


@pytest.mark.parametrize('question,expected', [
    ('Ngày 21/10/2026, điều kiện bồi thường thế nào?', set()),
    ('Ngày 02/04/2026 và 01/07/2025 có thay đổi không?', set()),
    ('Theo Quyết định 10/2026/QĐ-UBND ngày 18/01/2026?', {'10/2026'}),
    ('Luật 31/2024/QH15 và Nghị quyết 254/2025/QH15 áp dụng ngày 21/10/2026?', {'31/2024','254/2025'}),
])
def test_calendar_dates_never_request_an_unrelated_replacement(question, expected):
    from landlaw.agent import document_numbers_in_question
    assert document_numbers_in_question(question) == expected


def test_repeal_excerpt_retains_trigger_and_all_repealed_226_parts(source):
    excerpts, _ = provision_excerpts(source)
    repeal = excerpts[3]
    assert repeal['locator'] == 'Điều 16'
    assert repeal['text'].startswith('3. Các quy định sau đây hết hiệu lực')
    assert 'g1)' in repeal['text'] and 'g2) Phụ lục IV.' in repeal['text']
    assert '4. Thay thế các cụm từ' not in repeal['text']


def test_related_context_retains_parents_and_different_governing_articles():
    from conftest import document
    from landlaw.agent import diverse_related_context
    doc=document('rules')
    def item(ident, article):
        return Evidence(document=doc,chunk=doc.chunks[0].model_copy(update={'id':ident,'locator':f'Điều {article}'}),applicability='current')
    primary=[item('primary',1)]
    parent=item('parent',1)
    repeated=[item('fragment-'+str(i),2) for i in range(8)]
    governing=[item('condition',3),item('exception',4)]
    secondary=[parent,*repeated,*governing]
    reviewed={doc.id+':'+e.chunk.id:'fresh' for e in secondary}
    packed=diverse_related_context(primary,secondary,{'parent'},reviewed)[:8]
    assert packed[0].chunk.id=='parent'
    assert {'condition','exception'} <= {e.chunk.id for e in packed}
    assert len({e.chunk.id for e in packed})==len(packed)==8


def test_unreviewed_parent_cannot_displace_reviewed_article():
    from conftest import document
    from landlaw.agent import diverse_related_context
    doc=document('rules')
    parent=Evidence(document=doc,chunk=doc.chunks[0].model_copy(update={'id':'old-parent'}),applicability='current')
    rule=Evidence(document=doc,chunk=doc.chunks[0].model_copy(update={'id':'current-rule','locator':'Điều 2'}),applicability='current')
    result=diverse_related_context([], [parent,rule], {'old-parent'}, {doc.id+':current-rule':'fresh'})
    assert [e.chunk.id for e in result]==['current-rule','old-parent']
