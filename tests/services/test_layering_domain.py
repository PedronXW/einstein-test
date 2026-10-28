"""Testes TDD da feature F-031 (AC-003/AC-007/AC-008: vocabulário de domínio fora do model).

AC-003: FILE_STATUS_* expostos por services/file; DEFAULT_USER_MODEL por services/user.
AC-007: VectorRepository.search_similar exige chunks_per_file/max_chunks (sem defaults).
AC-008: repositories/__init__ não re-exporta de vector/; repositories/sqlalchemy inclui User.
"""

import inspect



def test_ac003_file_status_lives_in_service():
    from einstein_test.services.file import (
        FILE_STATUS_ERROR,
        FILE_STATUS_PENDING,
        FILE_STATUS_READY,
    )

    assert FILE_STATUS_PENDING == "pending"
    assert FILE_STATUS_READY == "ready"
    assert FILE_STATUS_ERROR == "error"


def test_ac003_file_status_not_in_model():
    import einstein_test.models.file as model

    assert not hasattr(model, "FILE_STATUS_PENDING")
    assert not hasattr(model, "FILE_STATUS_READY")
    assert not hasattr(model, "FILE_STATUS_ERROR")


def test_ac003_default_user_model_lives_in_service():
    from einstein_test.services.user import DEFAULT_USER_MODEL

    assert DEFAULT_USER_MODEL == "azure/gpt-5-mini"


def test_ac007_search_similar_requires_explicit_params():
    import inspect as _inspect

    from einstein_test.vector.repository import (
        VectorRepository,
        VectorRepositorySQLAlchemy,
    )

    for cls in (VectorRepository, VectorRepositorySQLAlchemy):
        sig = _inspect.signature(cls.search_similar)
        assert sig.parameters["chunks_per_file"].default is _inspect.Parameter.empty, (
            f"{cls.__name__}: chunks_per_file sem default"
        )
        assert sig.parameters["max_chunks"].default is _inspect.Parameter.empty, (
            f"{cls.__name__}: max_chunks sem default"
        )


def test_ac007_graph_is_single_source():
    import einstein_test.services.rag.graph as graph

    assert graph.CHUNKS_PER_FILE == 2
    assert graph.MAX_CHUNKS == 12


def test_ac008_repositories_init_does_not_reimport_vector():
    import einstein_test.repositories as repos

    src = inspect.getsource(repos)
    assert "einstein_test.vector.repository" not in src


def test_ac008_repositories_sqlalchemy_includes_user():
    import einstein_test.repositories.sqlalchemy as srepos

    assert "UserRepositorySQLAlchemy" in srepos.__all__
