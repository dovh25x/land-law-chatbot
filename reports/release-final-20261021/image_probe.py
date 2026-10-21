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
                    allow_stale_generation=False, source_lookup_only=True, generation_enabled=False)
sqlite = configuration_fingerprint(settings)
pg = configuration_fingerprint(settings.model_copy(update={
    'database_url': SecretStr('postgresql://fingerprint-only/metadata')}))
assert sqlite == 'dba699954ac85068b40f676eaa2c927065d81c406eda7b08a6665ffafc53e58e'
assert pg == '8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464'
assert not Path('/app/.env').exists()
assert not Path('/app/reports/final-submission').exists()
assert not Path('/app/reports/submission-20261021').exists()
assert not Path('/app/reports/release-final-20261021').exists()
assert len(list(Path('/app/reports/phase2c-current-20261021/receipts-final').glob('*.json'))) == 11
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
