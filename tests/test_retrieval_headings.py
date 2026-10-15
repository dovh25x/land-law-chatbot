from datetime import date
from conftest import document,release
from landlaw.security import digest
from landlaw.models import Chunk


def test_continuation_inherits_article_heading_without_body_terms(store):
    doc=document(text='Điều 1. Điều kiện bồi thường về đất 1. Đối tượng phải đáp ứng các điều kiện.');continuation='2. Có giấy chứng nhận hoặc các căn cứ hợp pháp khác.'
    doc.chunks.append(Chunk(id='law-2',document_id='law',text=continuation,locator='Điều 1',checksum=digest(continuation)))
    release(store,[doc])
    hits=store.search('điều kiện bồi thường về đất')
    assert {h.chunk.id for h in hits}=={'law-1','law-2'}


def test_historical_source_kept_but_current_rule_prioritized(store):
    old=document('old',text='Điều 1. Bồi thường cây trồng khi thu hồi đất.');old.effective_to=date(2025,1,1)
    new=document('new',text=old.chunks[0].text)
    release(store,[old,new])
    hits=store.search('bồi thường cây trồng',as_of=date(2026,1,1))
    assert hits[0].document.id=='new'
    assert {h.document.id for h in hits}=={'old','new'}
    hits=store.search('bồi thường cây trồng',as_of=date(2024,9,1))
    assert {h.document.id for h in hits}=={'old','new'}


def test_heading_suggestions_respect_project_and_time_but_keep_national(store):
    national=document();ring=document('ring',project='ring4');other=document('other',project='olympic');old=document('old');old.effective_to=date(2025,1,1)
    release(store,[national,ring,other,old])
    suggestions=store.article_candidates('điều kiện bồi thường','r1',date(2026,1,1),'ring4')
    assert {s['document_id'] for s in suggestions}=={'law','ring'}
    assert store.document('old','r1') is not None


def test_heading_cache_scoped_to_release(store):
    release(store,[document('first')],'r1');release(store,[document('second')],'r2')
    assert {h.document.id for h in store.search('bồi thường',release_id='r1')}=={'first'}
    assert {h.document.id for h in store.search('bồi thường',release_id='r2')}=={'second'}
