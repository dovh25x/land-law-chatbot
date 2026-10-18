
import pytest

from landlaw.config import Settings
from landlaw.evaluation import dataset, summarise


from landlaw.ingest import Quarantine, chunks_for, coverage, html_text, table_layout
from landlaw.security import official_url, redact


def test_loading_shell_and_metadata_not_legal_text():
    with pytest.raises(Quarantine):
        html_text(("<html><body>Portal VBPL Đang tải nội dung" + "x"*500 + "</body></html>").encode())
    with pytest.raises(Quarantine):
        html_text(("<article>Ngày ban hành: 01/01/2026 " + "metadata "*100 + "</article>").encode(), legal=True)




def test_reviewed_amendment_sequence_keeps_quoted_chapter_under_parent():
    pages = [(1,'Điều 1. Sửa đổi chương của luật cũ.\n“Chương IV\nĐiều 35. Nguyên tắc về đất đai.\nNội dung điều được thay thế.'),
             (2,'Điều 36. Quy hoạch được thay thế trong chương của luật cũ.”.\nĐiều 2. Chuyển tiếp về hồ sơ có trước ngày ban hành.\nĐiều 3. Hiệu lực từ ngày 01 tháng 01 năm 2019.')]
    chunks = chunks_for('amendment',pages,expected_article_count=3)
    assert {c.locator for c in chunks} == {'Điều 1','Điều 2','Điều 3'}
    assert any(c.locator=='Điều 1' and 'Điều 36.' in c.text for c in chunks)
    with pytest.raises(Quarantine,match='sequence incomplete'):
        chunks_for('amendment',pages[:1],expected_article_count=3)


def test_hanoi_archival_cdn_requires_official_publication_and_hanoi_path():
    url = 'https://storage-vnportal.vnpt.vn/gov-hni/6249/VanBanCongBao/source.pdf'
    assert official_url(url, 'https://congbao.hanoi.gov.vn/')
    assert not official_url(url)
    assert not official_url(url, 'https://example.com/')
    assert not official_url(url.replace('/gov-hni/', '/other-tenant/'), 'https://congbao.hanoi.gov.vn/')


def test_article_chunking_preserves_locator_and_parent():
    text = "Điều 4. " + "Điều kiện bồi thường theo hồ sơ. "*180
    chunks = chunks_for("law", [(2, text)])
    assert all(c.page == 2 and c.locator.startswith("Điều 4") for c in chunks)
    assert any(c.parent_id for c in chunks)
    assert all(c.checksum for c in chunks)


def test_attachment_pages_have_unique_ids_and_price_table_rows_survive():
    table = "[BẢNG / ĐƠN GIÁ — giữ dòng, tiêu đề, đơn vị]\nĐơn vị tính: nghìn đồng/m2\nSTT    Tên đường    Mức giá\n1      Đường A       12345\n" + "2      Đường B       67890\n"*80
    chunks = chunks_for("prices", [(1, table), (1, table)])
    assert len({c.id for c in chunks}) == len(chunks)
    assert all(c.page == 1 for c in chunks)
    assert all("Đơn vị tính" in c.text and "STT   Tên đường" in c.text for c in chunks)
    assert any("1   Đường A   12345" in c.text for c in chunks)




def test_aspnet_form_preserves_article_and_excludes_navigation():
    html = '<form><nav>menu</nav><div id="block_detail" class="document-detail">Điều 1. '+ 'Căn cứ thu hồi đất. '*60 + '</div><div class="related-news">unrelated</div></form>'
    text = html_text(html.encode(), legal=True)[0][1]
    assert "Điều 1" in text and "unrelated" not in text and "menu" not in text


def test_wrapped_cross_reference_keeps_actual_article_and_page_continuation():
    pages = [(1, "Điều 98. Bồi thường về đất ở\nNếu đủ điều kiện quy định tại\nĐiều 95 của Luật này thì được xem xét theo hồ sơ."),
             (2, "Tiếp tục nội dung quy định tại Điều 95 của Luật này.\nĐiều 99. Quy định đối với đất khác\nNội dung quy định tiếp theo được áp dụng.")]
    chunks = chunks_for("law", pages)
    first = next(c for c in chunks if "Điều 95 của" in c.text and c.page == 1)
    continuation = next(c for c in chunks if c.page == 2 and c.text.startswith("Tiếp tục"))
    assert first.locator == continuation.locator == "Điều 98"
    assert any(c.locator == "Điều 99" for c in chunks)
    assert not any(c.locator == "Điều 95" for c in chunks)


def test_wrapped_reference_with_period_does_not_relabel_amendment_body():
    text = ('Điều 7. Thay thế một số cụm từ\n'
            'Bãi bỏ cụm từ trong khoản 1\nĐiều 2.\n'
            '3. Thay thế cụm từ tại khoản 4\nĐiều 65.\n'
            'b) Bổ sung nội dung theo quy định.\n'
            'Điều 8.\nĐiều khoản chuyển tiếp\n1. Hồ sơ cũ được xem xét theo thời điểm.')
    chunks = chunks_for('amendment', [(35, text)])
    assert {chunk.locator for chunk in chunks} == {'Điều 7', 'Điều 8'}
    assert 'Điều 65.' in next(chunk.text for chunk in chunks if chunk.locator == 'Điều 7')


def test_unpunctuated_articles_and_appendix_preserve_distinct_locators_and_units():
    pages = [(1, 'Điều 1\nQuyết định chủ trương đầu tư dự án theo hồ sơ chính thức.\n'
                 'Điều 2\n1. Mục tiêu đầu tư theo nghị quyết được Quốc hội thông qua.\n'
                 'Thực hiện quy định tại\nĐiều 95 của Luật này khi giải quyết hồ sơ.'),
             (6, 'PHỤ LỤC\nĐơn vị tính: tỷ đồng\nTT   Dự án   Tổng mức đầu tư\n'
                 '1   Bồi thường, hỗ trợ, tái định cư   19.590\n'
                 '1.1   Hà Nội   13.370\n')]
    chunks = chunks_for('project', pages)
    assert {c.locator for c in chunks} == {'Điều 1', 'Điều 2', 'Trang 6'}
    appendix = next(c for c in chunks if c.page == 6)
    assert 'tỷ đồng' in appendix.text and '13.370' in appendix.text
    assert 'Điều 95 của' in next(c.text for c in chunks if c.locator == 'Điều 2')


def test_project_table_decimal_rows_are_not_repeated_as_headers():
    table = ('PHỤ LỤC\nĐơn vị tính: tỷ đồng\nTT   Dự án   Vốn đầu tư\n'
             '1.3   Bắc Ninh   2.480\n' + '2.1   Hà Nội   9.687\n'*100)
    chunks = [c for c in chunks_for('appendix', [(7, table)]) if not c.id.endswith('parent')]
    assert len(chunks) > 1
    assert sum(c.text.count('1.3   Bắc Ninh   2.480') for c in chunks) == 1
    assert all('Đơn vị tính: tỷ đồng' in c.text and 'TT   Dự án' in c.text for c in chunks)


def test_appendix_decision_templates_are_not_indexed_as_statutory_articles():
    pages = [(1, 'Điều 19. Hiệu lực thi hành\nQuy định có hiệu lực theo mốc được xác minh.'),
             (2, 'Phụ lục\n(Kèm theo Nghị định)\nMẫu số 14a\nQUYẾT ĐỊNH\nĐiều 1. Điền thông tin tạm đình chỉ.'),
             (3, 'Mẫu số 14b\nĐiều 2. Quyết định này có hiệu lực kể từ ngày ký.\nĐiều 3. Điền tên người thi hành.')]
    chunks = chunks_for('amending-decree', pages)
    assert {c.locator for c in chunks} == {'Điều 19', 'Trang 2', 'Trang 3'}
    assert any('Điều 2. Quyết định' in c.text and c.locator == 'Trang 3' for c in chunks)


def test_html_appendix_does_not_erase_operative_articles_before_it():
    html = '<article>Điều 31. Chuyển tiếp\n'+ 'Tiếp tục phương án đã phê duyệt. '*20 + '\nĐiều 32. Trách nhiệm thi hành\n' + 'Thực hiện theo thẩm quyền. '*20 + '\nPhụ lục\nMẪU QUYẾT ĐỊNH\nĐiều 1. Điền tên dự án trong mẫu.\n</article>'
    chunks = chunks_for('decree', html_text(html.encode(), legal=True))
    assert any(c.locator == 'Điều 31' and 'Tiếp tục phương án' in c.text for c in chunks)
    assert any(c.locator == 'Điều 32' and 'Thực hiện theo' in c.text for c in chunks)
    assert not any(c.locator == 'Điều 1' for c in chunks)
    assert all(not c.locator.startswith('Điều') for c in chunks if 'MẪU QUYẾT ĐỊNH' in c.text)


def test_table_marker_cache_does_not_turn_prose_into_table_or_repeat_rows():
    prose = "Điều 104. Bồi thường chi phí di chuyển\nỦy ban nhân dân cấp tỉnh quy định đơn giá bồi thường theo quy định của pháp luật."
    assert not table_layout(prose)
    assert all("[BẢNG" not in c.text for c in chunks_for("law", [(1, "[BẢNG / ĐƠN GIÁ — giữ dòng, tiêu đề, đơn vị; đối chiếu trang gốc]\n"+prose)]))
    table = "Đơn vị tính: nghìn đồng/m2\nSTT    Tên đường    Mức giá\n1      Đường A       12345\n2      Đường B       67890\n"
    chunk = chunks_for("prices", [(1, table)])[0]
    assert chunk.text.count("1   Đường A   12345") == 1
    assert "STT   Tên đường" in chunk.text
    many = chunks_for("prices", [(1, table+"3      Đường C       99999\n"*120)])
    assert sum(c.text.count("1   Đường A   12345") for c in many if not c.id.endswith("parent")) == 1


def test_source_allowlist_and_personal_identifier_redaction():
    assert official_url("https://datafiles.hanoi.gov.vn/law.pdf")
    assert not official_url("https://hanoi.gov.vn.evil.example/law.pdf")
    assert not official_url("http://127.0.0.1/a")
    assert not official_url("https://sqhx-hanoi.mediacdn.vn/a.pdf")
    assert official_url("https://sqhx-hanoi.mediacdn.vn/a.pdf", "https://hanoi.gov.vn/a")
    assert "person@example.com" not in redact("Email person@example.com; CCCD 012345678901")
    assert "012345678901" not in redact("CCCD 012345678901")


def test_production_rejects_local_storage_and_wildcard_cors():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production")


def test_benchmark_has_real_distinct_questions_and_no_fabricated_results():
    from pathlib import Path
    cases = dataset(Path("data/evaluation/smoke.jsonl"))
    assert len(cases) == 20
    assert len({c["question"] for c in cases}) == 20
    summary = summarise([], cases, "hash")
    assert not summary["acceptance_passed"]
    assert summary["results"][0]["completed"] == 0




def test_publication_requires_real_coverage_and_embeddings():
    report = coverage({"id": "empty", "documents": [], "checked_at": "2026-10-12"})
    assert not report["publication_ready"] and not report["coverage_passed"]


def test_resuming_preserves_failed_attempt_without_overwriting_it(tmp_path):
    import json
    from landlaw.evaluation import preserve_attempt
    failed={'case_id':'S01','mode':'agentic','result':{'status':'error','trace_id':'first'}}
    path=preserve_attempt(tmp_path,failed)
    original=path.read_bytes()
    assert preserve_attempt(tmp_path,failed)==path and path.read_bytes()==original
    succeeded={**failed,'result':{'status':'answered','trace_id':'second'}}
    next_path=preserve_attempt(tmp_path,succeeded)
    assert next_path!=path and len(list(tmp_path.glob('*.json')))==2
    assert json.loads(path.read_text())['record']['result']['status']=='error'


def test_benchmark_history_is_validated_without_database_writes(store):
    from landlaw.evaluation import validate_history
    from landlaw.models import ChatRequest
    history=[{'role':'user','content':'Văn bản nào?'},{'role':'assistant','content':'QĐ40.','citations':[{'document_id':'qd-40-2026-hanoi'}]}]
    validate_history(history)
    request=ChatRequest(session_id='a'*32,message='Văn bản đó thay thế văn bản nào?',history=history)
    assert request.history[1].citations[0].document_id=='qd-40-2026-hanoi'
    assert not store.rows("SELECT name FROM sqlite_master WHERE name='messages'")


def test_source_backup_includes_reviewed_ocr_and_original_provenance():
    from landlaw.cli import reviewed_source_files
    source={'raw_paths':['data/raw/source.pdf'],'raw_checksums':{'data/raw/source.pdf':'pdf'},
        'ocr_sidecars':[{'ocr_path':'data/raw/source.ocr.txt','ocr_sha256':'ocr','review_status':'verified'},
                       {'ocr_path':'data/raw/unreviewed.txt','ocr_sha256':'pending','review_status':'pending'}],
        'source_artifacts':[{'path':'data/raw/publication.html','sha256':'publication'}]}
    assert reviewed_source_files(source)==[('data/raw/source.pdf','pdf'),
        ('data/raw/source.ocr.txt','ocr'),('data/raw/publication.html','publication')]


@pytest.mark.asyncio
async def test_inline_publication_gazette_never_replaces_reviewed_pdf_attachment(settings,monkeypatch):
    import landlaw.ingest as ingestion
    from landlaw.security import digest
    approved=b'%PDF-reviewed-attachment';portal=b'%PDF-whole-publication-gazette'
    publication='https://vanban.chinhphu.vn/publication';attachment='https://datafiles.chinhphu.vn/approved.pdf';calls=[]
    async def download(client,url,publication_url=None):
        calls.append(url);return (approved if url==attachment else portal),url
    monkeypatch.setattr(ingestion,'download',download)
    monkeypatch.setattr(ingestion,'pdf_pages',lambda raw,ocr: [(1,'Điều 1. '+('Nội dung kiểm thử tài liệu và nguồn được đối chiếu. '*30))])
    source={'id':'reviewed-doc','title':'Technical fixture only','url':publication,'source_kind':'legal','review_status':'verified',
       'effective_from':'2024-08-01','attachment_urls':[attachment],'raw_checksums':{'approved.pdf':digest(approved)}}
    doc=await ingestion.collect_source(source,settings,None)
    assert calls==[publication,attachment] and doc.checksum==digest(approved)
    assert str(doc.source_files[0].url)==attachment


@pytest.mark.asyncio
async def test_reviewed_html_never_selects_unrelated_sidebar_pdf(settings,monkeypatch):
    import landlaw.ingest as ingestion
    from landlaw.security import digest
    url='https://xaydungchinhsach.chinhphu.vn/official-law'
    raw=('<article>Điều 1. '+('Nội dung pháp luật dùng làm fixture kiểm thử nguồn. '*30)+
         '</article><aside><a href="https://datafiles.chinhphu.vn/unrelated.pdf">Tin khác</a></aside>').encode()
    calls=[]
    async def download(client,link,publication_url=None):
        calls.append(link);assert link==url;return raw,link
    monkeypatch.setattr(ingestion,'download',download)
    source={'id':'html-doc','title':'Technical fixture only','url':url,'source_kind':'legal','review_status':'verified',
       'effective_from':'2024-08-01','raw_paths':['data/raw/html-doc.html'],'raw_checksums':{'html-doc.html':digest(raw)}}
    doc=await ingestion.collect_source(source,settings,None)
    assert calls==[url] and doc.checksum==digest(raw)


async def test_retrieval_benchmark_skips_no_gold_cases_and_never_generates_or_writes_sessions(store, settings, monkeypatch):
    from types import SimpleNamespace
    from conftest import release
    from landlaw.evaluation import evaluate_retrieval
    from landlaw.provider import GroqProvider
    import landlaw.evaluation as evaluation
    release(store)
    cases = [{'id': 'gold', 'question': 'điều kiện bồi thường', 'gold_chunk_ids': ['law-1']},
             {'id': 'scope', 'question': 'ngoài phạm vi', 'gold_chunk_ids': []}]
    monkeypatch.setattr(evaluation, 'frozen_dataset', lambda *_: (cases, 'frozen'))
    class LocalEncoder:
        def embed_many(self, texts, title, query):
            assert texts == ['điều kiện bồi thường'] and query is True
            return [[1.] + [0.] * 383]
    provider = SimpleNamespace(local_embeddings=LocalEncoder(), normalize_vector=GroqProvider.normalize_vector)
    report = await evaluate_retrieval(settings, store, provider)
    assert report['backend'] == 'sqlite'
    assert report['eligible_cases'] == report['hits'] == 1
    assert report['hit_rate'] == 1 and report['generation_calls'] == 0
    assert not store.rows('SELECT * FROM sessions')
    assert not store.rows('SELECT * FROM counters')


def test_ring4_coverage_uses_required_sources_and_project_evidence_not_other_projects():
    from conftest import document
    from landlaw.local_embedding import MODEL
    required = ['luat-dat-dai-2024','nd-88-2024','nd-226-2025','qd-56-2024-hanoi',
                'qd-40-2026-hanoi','nq-52-2025-hanoi']
    docs = [document(ident).model_dump(mode='json') for ident in required]
    docs.append(document('project',project='ring4').model_copy(update={'source_kind':'project_decision'}).model_dump(mode='json'))
    for doc in docs:
        doc['chunks'][0]['embedding'] = [1.0] + [0.0]*383
    payload = {'id':'reviewed','documents':docs,'checked_at':'2026-10-18','embedding_dimensions':MODEL['dimensions']}
    assert coverage(payload)['publication_ready']
    docs[-1]['project'] = 'olympic'
    assert not coverage(payload)['publication_ready']
    assert not coverage(payload)['scope_valid']
    docs[-1]['project'] = 'ring4'
    docs.pop(0)
    assert coverage(payload)['missing_mandatory_sources'] == ['luat-dat-dai-2024']
    assert not coverage(payload)['publication_ready']


def test_official_image_cdn_requires_verified_publication_context():
    assert official_url('https://xdcs.cdnchinhphu.vn/a.jpg','https://xaydungchinhsach.chinhphu.vn/a.htm')
    assert not official_url('https://xdcs.cdnchinhphu.vn/a.jpg')
    assert not official_url('https://xdcs.cdnchinhphu.vn.evil.example/a.jpg','https://hanoi.gov.vn/a')


@pytest.mark.parametrize('field', ['coverage_gaps', 'unresolved_relations'])
def test_coverage_blocks_publication_with_missing_dependencies(field):
    from conftest import document
    ids = ['luat-dat-dai-2024','nd-88-2024','nd-226-2025','qd-56-2024-hanoi',
           'qd-40-2026-hanoi','nq-52-2025-hanoi']
    docs = [document(ident).model_dump(mode='json') for ident in ids]
    project = document('ring4-evidence', project='ring4').model_copy(
        update={'source_kind':'project_decision'}).model_dump(mode='json')
    docs.append(project)
    for doc in docs:
        for chunk in doc['chunks']:
            chunk['embedding'] = [1.0] + [0.0]*383
    payload = {'id':'candidate','documents':docs,'embedding_dimensions':384,
               'checked_at':'2026-10-18T00:00:00Z',field:[{'pending':True}]}
    report = coverage(payload)
    assert report['coverage_passed'] and not report['publication_ready']
    assert not report['dependencies_complete']


@pytest.mark.asyncio
@pytest.mark.parametrize('numbers,scope,accepted', [
    ([2], 'Reviewed relevant policy page; full original retained.', True),
    ([2], '', False), ([0], 'reviewed', False), ([True], 'reviewed', False),
    ([4], 'reviewed', False), ([2, 2], 'reviewed', False),
    ([3, 2], 'reviewed', False),
])
async def test_reviewed_partial_pdf_preserves_physical_page_and_rejects_ambiguous_mapping(
        settings, numbers, scope, accepted):
    from pypdf import PdfWriter
    from landlaw.ingest import collect_source
    from landlaw.security import digest
    raw = settings.data_dir / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    pdf = raw / 'partial.pdf'
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=600, height=800)
    with pdf.open('wb') as stream:
        writer.write(stream)
    text = raw / 'partial.txt'
    text.write_text('Điều 2. ' + 'Nội dung quy định có đối chiếu bản gốc. '*25)
    source = {'id':'partial', 'title':'Technical fixture', 'url':'https://hanoi.gov.vn/fixture',
        'source_kind':'legal', 'review_status':'verified', 'effective_from':'2024-08-01',
        'checked_at':'2026-10-18T00:00:00+00:00', 'raw_paths':[str(pdf)],
        'raw_checksums':{str(pdf):digest(pdf.read_bytes())},
        'ocr_sidecars':[{'ocr_path':str(text), 'ocr_sha256':digest(text.read_bytes()),
            'pdf_sha256':digest(pdf.read_bytes()), 'review_status':'verified',
            'page_numbers':numbers, 'scope_review':scope}]}
    if accepted:
        doc = await collect_source(source, settings, None, offline=True)
        assert all(chunk.page == 2 for chunk in doc.chunks)
    else:
        with pytest.raises(Quarantine, match='page count mismatch'):
            await collect_source(source, settings, None, offline=True)
