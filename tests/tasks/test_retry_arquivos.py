"""Testes TDD da feature F-020 (retry no processamento de arquivos).

Valida: task configurada com autoretry/backoff; erro permanente sem retry;
idempotência (ready -> skip); error_detail após esgotar. O retry transiente é
coberto verificando que o modo eager de `apply` tenta novamente.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from einstein_test.db.base import Base
from einstein_test.models.file import File
from einstein_test.models.file_chunk import FileChunk
from einstein_test.repositories.file import FileRepositorySQLAlchemy
from einstein_test.storage import set_storage, InMemoryStorage
from einstein_test.vector import FakeEmbedder, set_embedder
from einstein_test.tasks import vectorize_file, celery_app


@pytest.fixture
def env(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    storage = InMemoryStorage()
    set_storage(storage)
    set_embedder(FakeEmbedder())

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    import einstein_test.api.dependencies as deps

    monkeypatch.setattr(deps, "create_engine_from_config", lambda url=None: engine)

    # eager: .apply executa de forma síncrona (com retry se configurado)
    celery_app.conf.task_always_eager = True

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
    return file_, key, content


def test_ac001_task_configured_with_autoretry_backoff():
    from einstein_test.tasks import VECTORIZE_MAX_RETRIES, celery_app, vectorize_file

    # task registrada no app
    assert vectorize_file.name in celery_app.tasks
    # backoff configurado (contagem crescente) + max_retries default > 0
    assert VECTORIZE_MAX_RETRIES >= 1
    import einstein_test.tasks as tasks_mod

    content = open(tasks_mod.__file__, encoding="utf-8").read()
    assert "self.retry(exc=exc, countdown=delay)" in content, "retry com countdown"
    assert "2 ** self.request.retries" in content, "backoff exponencial"
    assert "VECTORIZE_MAX_RETRIES" in content, "max_retries configurável"


def test_ac002_permanent_error_no_retry_sets_error(env):
    env["storage"]
    with Session(env["engine"]) as s:
        repo = FileRepositorySQLAlchemy(s)
        file_ = repo.create(
            chat_id=1, name="x.txt", url="not-an-s3-url",
            type="text/plain", size=1,
        )
        file_id = file_.id
        s.commit()
        s.expunge_all()

    result = env["task"].apply(args=[file_id], throw=False)
    assert result.result["status"] == "error"
    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.status == "error"
        assert updated.error_detail == "url inválida do arquivo"


def test_ac003_idempotent_no_reprocess(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        file_, key, content = _create_file(s)
        file_id = file_.id
        f = s.get(File, file_id)
        f.status = "ready"
        f.chunk_ids = [4, 5, 6]
        f.vector_reference = "vec-xyz"
        s.commit()
        s.expunge_all()
    storage.upload("einstein", key, content)

    result = env["task"].apply(args=[file_id], throw=False)
    assert result.result["status"] == "ready", "já ready -> não reprocessa"
    with Session(env["engine"]) as s:
        rows = s.query(FileChunk).filter(FileChunk.file_id == file_id).all()
        assert len(rows) == 0, "arquivo ready não gera novos chunks"


def test_ac004_transient_error_eventually_succeeds(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        file_, key, content = _create_file(s)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    calls = {"n": 0}

    class _FlakyEmbedder:
        def embed(self, texts):
            calls["n"] += 1
            if calls["n"] <= 1:
                raise ConnectionError("timeout transiente")
            return FakeEmbedder().embed(texts)

    set_embedder(_FlakyEmbedder())
    # eager com retry: a task é re-enfileirada e re-executada
    result = env["task"].apply(args=[file_id], throw=False)
    assert result.result["status"] == "ready", "retry transiente resultou em sucesso"
    assert calls["n"] >= 1, "houve ao menos 1 tentativa"
    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.status == "ready"


def test_ac004_max_retries_exhausted_sets_error(env):
    storage = env["storage"]
    with Session(env["engine"]) as s:
        file_, key, content = _create_file(s)
        file_id = file_.id
        s.expunge_all()
    storage.upload("einstein", key, content)

    class _AlwaysFail:
        def embed(self, texts):
            raise ConnectionError("LLM fora do ar")

    set_embedder(_AlwaysFail())
    result = env["task"].apply(args=[file_id], throw=False)
    assert result.result["status"] == "error"
    with Session(env["engine"]) as s:
        updated = s.get(File, file_id)
        assert updated.status == "error"
        assert updated.error_detail, "error_detail preenchido"