import uuid
from datetime import date

import pytest

from landlaw.config import Settings
from landlaw.models import Chunk, Document
from landlaw.security import digest, new_token, utcnow
from landlaw.store import Store


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
                    llm_provider='gemini', embedding_provider='gemini', embedding_model='gemini-embedding-2',
                    embedding_dimensions=768, groq_api_key='', cloudflare_ai_api_token='',
                    backup_encryption_key='', supabase_url='', supabase_service_role_key='',
                    sqlite_path=str(tmp_path / "local.db"), data_dir=tmp_path / "data",
                    reports_dir=tmp_path / "reports", gemini_api_key="test-key", ip_hash_secret="a"*32)


@pytest.fixture
def store(settings):
    repo = Store(settings)
    yield repo
    repo.close()


def document(doc_id="law", text="Điều 1. Điều kiện bồi thường khi thu hồi đất phải được kiểm tra theo hồ sơ.", **kwargs):
    chunk = Chunk(id=f"{doc_id}-1", document_id=doc_id, text=text, locator="Điều 1", checksum=digest(text))
    return Document(id=doc_id, title=f"Văn bản {doc_id}", url="https://vanban.chinhphu.vn/?docid=1",
                    source_kind="legal", jurisdiction="national", checked_at=utcnow(), checksum=digest(doc_id),
                    effective_from=date(2024, 8, 1), applicability_verified=True, chunks=[chunk], **kwargs)


def release(repo, docs=None, release_id="r1", relations=None):
    payload = {"id": release_id, "checked_at": utcnow().isoformat(), "documents": [d.model_dump(mode="json") for d in docs or [document()]],
               "relations": relations or [], "embedding_model": "gemini-embedding-2", "embedding_dimensions": 768}
    repo.stage(payload)
    repo.publish(release_id)
    return payload


def session(repo):
    sid, token = str(uuid.uuid4()), new_token()
    repo.create_session(sid, token)
    return sid, token
