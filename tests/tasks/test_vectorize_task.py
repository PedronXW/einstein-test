"""Testes TDD da feature F-015 (AC-004/AC-005: task Celery vectorize_file).

Valida que a task baixa o conteúdo do storage e vetoriza, atualizando
File.status -> ready (com chunk_ids) ou error (com error_detail). Sem broker:
a task é executada de forma síncrona via .apply().
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.storage import set_storage, InMemoryStorage
from einstein_test.vector import FakeEmbedder, set_embedder


@pytest.fixture
def env(monkeypatch, tmp_path):
    from einstein_test.tasks import vectorize_file

    # engine/db em arquivo compartilhado entre fixture e task
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    storage = InMemoryStorage()
    set_storage(storage)
    set_embedder(FakeEmbedder())

    # a task abre seu próprio engine via create_engine_from_config(); forçamos
    # o mesmo sqlite de arquivo via DATABASE_URL e monkeypatch do engine.
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    # task usa create_engine_from_config (db/engine) -> force monkeypatch
    import einstein_test.db.engine as db_engine

    monkeypatch.setattr(db_engine, "create_engine_from_config", lambda url=None: engine)

    yield {"engine": engine, "storage": storage, "db_file": db_file,
           "task": vectorize_file}
    engine.dispose()


def _create_file(session, name="nota.txt", content=b"texto longo " * 20):
    import uuid

    key = f"chats/1/{uuid.uuid4().hex}/{name}"
    repo = FileRepositorySQLAlchemy(session)
    file_ = repo.create(
        chat_id=1, name=name, url=f"s3://einstein/{key}",
        type="text/plain", size=len(content),
    )
    session.commit()
    return file_, key


def test_ac004_storage_download_new():
    from einstein_test.storage import Storage

    assert hasattr(Storage, "download"), "Storage.download existe no Protocol"


def test_ac004_storage_inmemory_download(env):
    storage = env["storage"]
    storage.upload("einstein", "chats/1/x/a.txt", b"ola mundo")
    assert storage.download("einstein", "chats/1/x/a.txt") == b"ola mundo"


def test_ac004_task_vectorizes_file(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        content = b"texto longo " * 20
        file_, key = _create_file(s, content=content)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    result = env["task"].apply(args=[file_id])
    assert result.successful(), result.traceback

    with Session(env["engine"]) as s:
        s.expire_all()
        updated = s.get(File, file_id)
        assert updated.status == "ready", "status ready após vetorizar"
        assert updated.chunk_ids, "chunk_ids populados"
        assert updated.vector_reference, "vector_reference populado"
        assert updated.error_detail is None


def test_ac005_task_error_sets_error(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        content = b"texto "
        file_, key = _create_file(s, content=content)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    class _BoomEmbedder:
        def embed(self, texts):
            raise RuntimeError("embedding falhou")

    set_embedder(_BoomEmbedder())
    result = env["task"].apply(args=[file_id])
    assert result.successful(), "task não re-levanta (captura erro)"

    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.status == "error", "status error"
        assert updated.error_detail, "error_detail preenchido"


def test_ac005_task_missing_file_returns_missing(env):
    result = env["task"].apply(args=[999999])
    assert result.successful()
    assert result.result["status"] == "missing"


def test_ac005_task_invalid_url_sets_error(env):
    with Session(env["engine"]) as s:
        repo = FileRepositorySQLAlchemy(s)
        file_ = repo.create(
            chat_id=1, name="x.txt", url="not-an-s3-url",
            type="text/plain", size=1,
        )
        file_id = file_.id
        s.commit()
        s.expunge_all()

    result = env["task"].apply(args=[file_id])
    assert result.successful()
    assert result.result["status"] == "error"

    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.status == "error"
        assert updated.error_detail == "url inválida do arquivo"


def test_ac005_task_error_detail_is_class_name(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        content = b"texto "
        file_, key = _create_file(s, content=content)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    class _BoomEmbedder:
        def embed(self, texts):
            raise RuntimeError("embedding falhou")

    set_embedder(_BoomEmbedder())
    env["task"].apply(args=[file_id])

    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.error_detail == "RuntimeError", "só o nome da classe"
        assert "embedding falhou" not in (updated.error_detail or ""), (
            "não vaza a mensagem interna"
        )


def test_ac004_task_result_contract(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        content = b"texto longo " * 15
        file_, key = _create_file(s, content=content)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    result = env["task"].apply(args=[file_id])
    assert result.successful()
    assert result.result["file_id"] == file_id
    assert result.result["status"] == "ready"
    assert result.result["chunks"] > 0


def test_ac005_task_idempotent_second_run(env):
    # segunda execução em arquivo ready não duplica chunks nem quebra
    storage = env["storage"]
    with Session(env["engine"]) as s:
        content = b"texto longo " * 15
        file_, key = _create_file(s, content=content)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    r1 = env["task"].apply(args=[file_id])
    assert r1.result["status"] == "ready"
    first_chunks = r1.result["chunks"]

    r2 = env["task"].apply(args=[file_id])
    assert r2.result["status"] == "ready", "re-processo é idempotente"

    with Session(env["engine"]) as s:
        from einstein_test.models.file_chunk import FileChunk

        rows = s.query(FileChunk).filter(FileChunk.file_id == file_id).all()
        assert len(rows) == first_chunks, (
            "chunks não duplicados na segunda execução"
        )