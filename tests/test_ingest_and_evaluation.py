
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
    cases = dataset(Path("data/evaluation/questions.jsonl"))
    assert len(cases) == 120
    assert sum(c["split"] == "dev" for c in cases) == 40
    assert sum(c["split"] == "acceptance" for c in cases) == 80
    assert len({c["question"] for c in cases}) == 120
    summary = summarise([], cases, "hash")
    assert not summary["acceptance_passed"]
    assert summary["results"][0]["recall_at_8"] is None


def test_frozen_benchmark_rejects_edited_gold_and_source_content(tmp_path):
    import json
    from pathlib import Path
    from landlaw.evaluation import validate_frozen_benchmark
    root = Path('data/evaluation')
    paths = [tmp_path/name for name in ('questions.jsonl', 'acceptance-freeze.json', 'gold-sources.json')]
    for path in paths:
        path.write_bytes((root/path.name).read_bytes())
    assert validate_frozen_benchmark(*paths)['acceptance_cases'] == 80
    original = paths[0].read_bytes()
    paths[0].write_bytes(original.replace(b'HL-041', b'HL-999', 1))
    with pytest.raises(ValueError, match='freeze mismatch'):
        validate_frozen_benchmark(*paths)
    paths[0].write_bytes(original)
    sources = json.loads(paths[2].read_text())
    next(iter(sources['passages'].values()))['text'] += ' unauthorized edit'
    paths[2].write_text(json.dumps(sources))
    with pytest.raises(ValueError, match='freeze mismatch'):
        validate_frozen_benchmark(*paths)


def test_publication_requires_real_coverage_and_embeddings():
    report = coverage({"id": "empty", "documents": [], "checked_at": "2026-10-12"})
    assert not report["publication_ready"] and not report["coverage_passed"]


def test_resuming_preserves_failed_attempt_without_overwriting_it(tmp_path):
    import json
    from landlaw.evaluation import preserve_attempt
    failed={'case_id':'S01','mode':'baseline','result':{'status':'error','trace_id':'first'}}
    path=preserve_attempt(tmp_path,failed)
    original=path.read_bytes()
    assert preserve_attempt(tmp_path,failed)==path and path.read_bytes()==original
    succeeded={**failed,'result':{'status':'answered','trace_id':'second'}}
    next_path=preserve_attempt(tmp_path,succeeded)
    assert next_path!=path and len(list(tmp_path.glob('*.json')))==2
    assert json.loads(path.read_text())['record']['result']['status']=='error'


def test_paired_benchmark_history_is_fixed_labelled_and_isolated(store):
    from landlaw.evaluation import seed_history
    from conftest import session
    first, _ = session(store)
    second, _ = session(store)
    untouched, _ = session(store)
    fixture = [{'role':'user','content':'Văn bản nào?'},
               {'role':'assistant','content':'Tình huống tham chiếu QĐ40.',
                'citations':[{'document_id':'qd-40-2026-hanoi','locator':'Điều 2'}]}]
    for sid in (first, second):
        seed_history(store, sid, fixture)
    displayed = lambda sid: [(m['role'], m['payload']) for m in store.messages(sid)]
    assert displayed(first) == displayed(second)
    assert [role for role, _ in displayed(first)] == ['user', 'assistant']
    assert all(payload['benchmark_fixture'] for _, payload in displayed(first))
    assert not store.messages(untouched)
    assert not store.rows('SELECT * FROM traces')
    assert not store.rows('SELECT * FROM counters')
    with pytest.raises(ValueError, match='alternating'):
        seed_history(store, first, ['A previous turn requiring an unmeasured LLM call'])
    assert len(store.messages(first)) == 2


def test_source_backup_includes_reviewed_ocr_and_original_provenance():
    from landlaw.cli import reviewed_source_files
    source={'raw_paths':['data/raw/source.pdf'],'raw_checksums':{'data/raw/source.pdf':'pdf'},
        'ocr_sidecars':[{'ocr_path':'data/raw/source.ocr.txt','ocr_sha256':'ocr','review_status':'verified'},
                       {'ocr_path':'data/raw/unreviewed.txt','ocr_sha256':'pending','review_status':'pending'}],
        'source_artifacts':[{'path':'data/raw/publication.html','sha256':'publication'}]}
    assert reviewed_source_files(source)==[('data/raw/source.pdf','pdf'),
        ('data/raw/source.ocr.txt','ocr'),('data/raw/publication.html','publication')]
