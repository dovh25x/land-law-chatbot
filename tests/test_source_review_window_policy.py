"""Boundary tests for the proposed 72-hour source-review window.

These tests exercise the existing scoped receipt gate; they do not enable the
proposed policy in production or alter any receipt outside the test database.
"""
import json
from datetime import date

import pytest

from conftest import document, release
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.security import utcnow


def install_window(store, payload, doc, tmp_path, start, end):
    receipt = {
        'document_id': doc.id,
        'checksum': doc.checksum,
        'checked_at': utcnow().isoformat(),
        'status': 'unchanged',
        'evidence_urls': [str(doc.url)],
        'relation_review': 'Reviewed only the named passages and date interval.',
        'verified_scope': [{
            'as_of_from': str(start),
            'as_of_to': str(end),
            'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum},
        }],
    }
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps(receipt))
    pinned = record_source_review(store, path)
    policy = {'version': 1, 'release_id': payload['id'],
              'receipts': {doc.id: pinned['receipt_sha256']}}
    path = tmp_path / 'gate.json'
    path.write_text(json.dumps(policy))
    activate_source_gate(store, path)


@pytest.mark.parametrize('as_of,usable', [
    ('2026-10-22', True),
    ('2026-10-23', True),
    ('2026-10-24', True),
    ('2026-10-25', False),
    ('2026-10-26', False),
])
def test_72_hour_window_is_usable_until_exclusive_end(store, tmp_path, as_of, usable):
    doc = document()
    payload = release(store, [doc])
    install_window(store, payload, doc, tmp_path,
                   date(2026, 10, 22), date(2026, 10, 25))

    gate = store.source_gate_status(payload, as_of=date.fromisoformat(as_of))

    assert gate['usable'] is usable
    assert gate['eligible_passages'] == (1 if usable else 0)


def test_72_hour_window_is_not_usable_for_an_earlier_date(store, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_window(store, payload, doc, tmp_path,
                   date(2026, 10, 22), date(2026, 10, 25))

    gate = store.source_gate_status(payload, as_of=date(2026, 10, 21))

    assert gate['usable'] is False
    assert gate['eligible_passages'] == 0
