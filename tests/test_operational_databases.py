"""Isolated validation databases must survive both failure paths without DROP."""
import json
from types import SimpleNamespace

import pytest
from psycopg.conninfo import conninfo_to_dict
from pydantic import SecretStr

from scripts import evaluate_corpus_candidate, evaluate_generation_candidate, verify_postgres_database


class ValidationFailure(RuntimeError):
    pass


@pytest.mark.parametrize('helper_name', ['generation', 'corpus', 'runtime'])
@pytest.mark.parametrize('failure_point', ['migration', 'validation'])
async def test_isolated_validation_retains_database_and_closes_connections(
        tmp_path, settings, monkeypatch, helper_name, failure_point):
    monkeypatch.chdir(tmp_path)
    migrations = tmp_path/'migrations'
    migrations.mkdir()
    (migrations/'001.sql').write_text('VALIDATION_MIGRATION')
    owner = 'postgresql://owner@localhost/serving'
    settings = settings.model_copy(update={'admin_database_url': SecretStr(owner),
                                           'database_url': SecretStr(owner)})
    commands, connections = [], []

    class Connection:
        def __init__(self, connection):
            self.database = conninfo_to_dict(connection)['dbname']
            self.closed = False
            connections.append(self)
        def __enter__(self): return self
        def __exit__(self, *_): self.closed = True
        def execute(self, command):
            rendered = command if isinstance(command, str) else command.as_string()
            commands.append(rendered)
            if rendered == 'VALIDATION_MIGRATION' and failure_point == 'migration':
                raise ValidationFailure('migration failed')
            return self
        def fetchone(self): return (self.database,)

    def connect(connection, **_): return Connection(connection)
    helper = {'generation': evaluate_generation_candidate, 'corpus': evaluate_corpus_candidate,
              'runtime': verify_postgres_database}[helper_name]
    monkeypatch.setattr(helper.psycopg, 'connect', connect)
    monkeypatch.setattr(helper, 'Settings', lambda: settings)
    output = tmp_path/'output'
    expected = {'id': 'fixture', 'documents': []}
    snapshot = tmp_path/'candidate.json'
    snapshot.write_text(json.dumps(expected))
    backup = tmp_path/'backup.json'
    backup.write_text(json.dumps({'state': [{'key': 'active_release', 'value': 'fixture'}],
                                 'releases': [{'id': 'fixture', 'payload': 'fixture'}]}))
    try:
        with pytest.raises(ValidationFailure):
            if helper_name == 'generation':
                output.mkdir()
                with helper.candidate_settings(SimpleNamespace(postgres=True, output=output), tmp_path):
                    raise ValidationFailure('validation failed')
            elif helper_name == 'corpus':
                monkeypatch.setattr(helper, 'validate_corpus', lambda _: None)
                async def evaluate(selected, *_):
                    if selected.database_url.get_secret_value():
                        raise ValidationFailure('validation failed')
                monkeypatch.setattr(helper, 'evaluate_store', evaluate)
                await helper.main(SimpleNamespace(output=output, snapshot=snapshot, backup=backup, postgres=True))
            else:
                monkeypatch.setattr(helper, 'dotenv_values', lambda _: {'ADMIN_DATABASE_URL': owner, 'DATABASE_URL': owner})
                class Store:
                    @staticmethod
                    def decode_release(_): return expected
                    def __init__(self, *_): raise ValidationFailure('validation failed')
                monkeypatch.setattr(helper, 'Store', Store)
                helper.main(backup, output/'runtime.json')
    finally:
        assert sum(command.startswith('CREATE DATABASE') for command in commands) == 1
        assert not any(command.startswith('DROP DATABASE') for command in commands)
        assert connections and all(connection.closed for connection in connections)
        receipts = list(output.rglob('*.jsonl'))
        assert len(receipts) == 1
        retained = json.loads(receipts[0].read_text())
        assert retained['database'] != 'serving' and retained['automatic_drop'] is False
        assert owner not in receipts[0].read_text()
