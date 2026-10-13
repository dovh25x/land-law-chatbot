"""Technical fixtures only: these vectors never enter a legal corpus."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

spec = importlib.util.spec_from_file_location("offline_colab", Path("scripts/offline_e5_colab.py"))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def bundle(tmp_path):
    source = tmp_path/"source.json"
    source.write_text(json.dumps({"id": "fixture", "documents": [{"id": "law", "title": "Fixture",
        "chunks": [{"id": str(i), "text": text, "checksum": worker.sha(text.encode()),
                    "locator": "Điều 1"} for i, text in enumerate(("First test passage", "Second test passage"))]}]}))
    path = tmp_path/"input.zip"
    worker.export_bundle(source, path)
    return path


def test_colab_resume_repairs_torn_checkpoint_and_validates_complete_output(tmp_path, monkeypatch):
    class FixtureEncoder:
        def __init__(self, *args): pass
        def encode(self, text): return [1.0]+[0.0]*383
    monkeypatch.setattr(worker, "Encoder", FixtureEncoder)
    source = bundle(tmp_path)
    work_dir, output = tmp_path/"job", tmp_path/"result.zip"
    partial = worker.run_job(source, work_dir, output, tmp_path/"models", limit=1)
    assert partial['status'] == 'partial' and partial['completed_chunks'] == 1
    assert not output.exists()
    with (work_dir/"checkpoints.jsonl").open('ab') as ledger:
        ledger.write(b'{"interrupted":')
    complete = worker.run_job(source, work_dir, output, tmp_path/"models")
    assert complete['status'] == 'complete' and complete['newly_embedded'] == 1
    assert worker.validate_output(source, output)['completed_chunks'] == 2
    class NeverLoad:
        def __init__(self, *args): raise AssertionError('A fully cached job must not download/load a model')
    monkeypatch.setattr(worker, "Encoder", NeverLoad)
    assert worker.run_job(source, work_dir, output, tmp_path/"models")['newly_embedded'] == 0


def test_colab_rejects_different_contract_and_corrupt_vectors(tmp_path, monkeypatch):
    source = bundle(tmp_path)
    work_dir = tmp_path/"job"
    work_dir.mkdir()
    (work_dir/"job.json").write_text('{}')
    with pytest.raises(ValueError, match='different input'):
        worker.run_job(source, work_dir, tmp_path/'result.zip', tmp_path/'models')
    assert not worker.vector_valid([1.0]+[0.0]*767)
    assert not worker.vector_valid([float('nan')]+[0.0]*383)
    assert not worker.vector_valid([0.0]*384)
    ledger = tmp_path/'ledger.jsonl'
    ledger.write_text(json.dumps({'key': 'a'*64, 'embedding': [1.0]+[0.0]*383})+'\n'
                      +json.dumps({'key': 'a'*64, 'embedding': [-1.0]+[0.0]*383})+'\n')
    with pytest.raises(ValueError, match='Conflicting'):
        worker.read_ledger(ledger)


def test_colab_notebook_matches_export_worker_and_cells_compile():
    notebook = json.loads(Path('notebooks/colab_cpu_embeddings.ipynb').read_text())
    checksum = hashlib.sha256(Path('scripts/offline_e5_colab.py').read_bytes()).hexdigest()
    code = ''.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code')
    assert checksum in code
    assert 'GEMINI_API_KEY' not in code and 'SUPABASE_SERVICE_ROLE_KEY' not in code
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), '<notebook>', 'exec')
