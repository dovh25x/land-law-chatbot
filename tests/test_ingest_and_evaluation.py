
import pytest

from landlaw.config import Settings
from landlaw.evaluation import dataset, summarise
from landlaw.ingest import Quarantine, chunks_for, coverage, html_text
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


def test_publication_requires_real_coverage_and_embeddings():
    report = coverage({"id": "empty", "documents": [], "checked_at": "2026-10-12"})
    assert not report["publication_ready"] and not report["coverage_passed"]
