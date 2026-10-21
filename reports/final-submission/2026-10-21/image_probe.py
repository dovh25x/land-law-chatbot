"""Read-only packaging/identity checks in the serving image; network disabled."""
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.local_embedding import MODEL
from pydantic import SecretStr

settings = Settings(_env_file=None, database_url='', admin_database_url='', groq_api_key='',
                    allow_stale_generation=False)
sqlite = configuration_fingerprint(settings)
pg = configuration_fingerprint(settings.model_copy(update={
    'database_url': SecretStr('postgresql://fingerprint-only/metadata')}))
assert sqlite == '1697d9dec78b8625398e53999b609e3ce57258666c2e3566a8321385abe8886d'
assert pg == '2229a1b298052e51b80d1d46530ca9a5ba580f5bc1b04be90cecdf0e15190c6d'
assert not Path('/app/.env').exists()
assert not Path('/app/reports/final-submission').exists()
assert not list(Path('/app/reports').glob('phase3b-*/local-corpus-backup.json'))
assert Path('/app/reports/latest.json').is_file()
assert Path('/app/reports/public-evaluations.json').is_file()
model_files = {}
for name, expected in [('model_quantized.onnx', MODEL['onnx_sha256']),
                       ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
    actual = hashlib.sha256((Path('/app/models/e5') / name).read_bytes()).hexdigest()
    assert actual == expected
    model_files[name] = actual
check = subprocess.run(['python', '-m', 'pip', 'check'], check=False, capture_output=True, text=True)
assert check.returncode == 0
assert os.geteuid() == 10001
print(json.dumps({'status': 'PASS', 'python': platform.python_version(), 'uid': os.geteuid(),
    'sqlite_fingerprint': sqlite, 'postgresql_configuration_fingerprint': pg,
    'pinned_model_checksums': model_files, 'pip_check': check.stdout.strip(),
    'academic_reports_excluded': True, 'duplicate_backup_excluded': True,
    'public_report_inputs_present': True, 'dotenv_absent': True,
    'external_llm_requests': 0, 'scope': 'Read-only serving image identity and files, network=none; not database or model inference'}))
