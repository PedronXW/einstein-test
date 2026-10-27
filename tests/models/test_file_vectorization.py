"""Testes TDD da feature F-010 (AC-005: model File com campos vetoriais).

Valida que File ganha chunk_ids (JSONB) e vector_reference (str nullable),
registradas na Base, sem quebrar os campos existentes.
"""

from einstein_test.db.base import Base
from einstein_test.models import Chat, File, Message  # noqa: F401


def test_ac005_file_has_chunk_ids_column():
    assert "chunk_ids" in File.__table__.c, "File.chunk_ids existe"


def test_ac005_file_has_vector_reference_column():
    assert "vector_reference" in File.__table__.c, "File.vector_reference existe"
    assert File.__table__.c.vector_reference.nullable is True, "vector_reference nullable"


def test_ac005_chunk_ids_default_empty_list():
    col = File.__table__.c.chunk_ids
    assert col.default is not None or col.server_default is not None, (
        "chunk_ids tem default (lista vazia)"
    )


def test_ac005_file_chunk_registered_on_base():
    assert "file_chunks" in Base.metadata.tables, "tabela file_chunks registrada"


def test_ac005_existing_columns_preserved():
    cols = {c.name for c in File.__table__.columns}
    assert {"id", "name", "url", "type", "size", "chat_id",
            "created_at", "updated_at", "deleted_at"} <= cols