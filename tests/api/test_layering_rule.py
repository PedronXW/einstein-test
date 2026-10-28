"""Testes TDD da feature F-031 (AC-001: prova estrutural da regra de ouro).

A regra do projeto: controller(api) -> service -> repository -> model.
Controllers montam repositórios SOMENTE para injetar no service (DI), nunca
chamam método de repository/model diretamente nem contêm regra de negócio.
Este teste é a prova mecânica dessa fronteira.
"""

import inspect
import re

import einstein_test.api.auth as auth_api
import einstein_test.api.auth_router as auth_router_api
import einstein_test.api.chats as chats_api
import einstein_test.api.files as files_api
import einstein_test.api.messages as messages_api


def _api_sources() -> dict[str, str]:
    return {
        "auth": inspect.getsource(auth_api),
        "auth_router": inspect.getsource(auth_router_api),
        "chats": inspect.getsource(chats_api),
        "files": inspect.getsource(files_api),
        "messages": inspect.getsource(messages_api),
    }


# Chamadas diretas repo(...).metodo( — proibidas no controller.
_FORBIDDEN = re.compile(
    r"\b(?:Chat|File|Message|User|Vector)RepositorySQLAlchemy\("
    r"[^)]*\)\.(?:get_by_|create|list|delete|search_similar|insert_|update_)"
)


def test_ac001_controllers_never_call_repository_methods_directly():
    violations = {}
    for name, src in _api_sources().items():
        matches = _FORBIDDEN.findall(src)
        if matches:
            violations[name] = matches
    assert not violations, (
        f"controllers chamando repository direto (quebram a regra de ouro): {violations}"
    )


def test_ac001_repository_usages_are_only_di_into_service():
    # Toda instanciação de `*RepositorySQLAlchemy(` nos controllers precisa estar
    # como argumento de um construtor de service (DI). Proibimos padrões como
    # `ChatRepositorySQLAlchemy(session).get_by_id(` (já coberto) e garantimos
    # que cada `RepoSQLAlchemy(session)` esteja cercado por `Service(`.
    import re as _re

    service_wrapper = _re.compile(
        r"\b(?:User|Auth|Chat|Message|File)Service\(|get_rag_service\("
    )
    for name, src in _api_sources().items():
        instantiations = _re.findall(
            r"\b\w+RepositorySQLAlchemy\(\s*session\s*\)", src
        )
        for occ in instantiations:
            assert service_wrapper.search(src), (
                f"{name}: repo instanciado fora de service (DI) -> {occ!r}"
            )


def test_ac001_business_rules_not_in_controllers():
    # regras de negócio de domínio (limites/status/constantes de produto) não
    # devem ser definidas nos controllers — devem vir de services.
    for name, src in _api_sources().items():
        assert "MAX_UPLOAD_SIZE =" not in src, f"{name}: limite de upload no controller"
        assert "MAX_FILES_PER_BATCH =" not in src, f"{name}: limite de lote no controller"
        assert "DEFAULT_USER_MODEL =" not in src, f"{name}: constante de produto no controller"
        assert "FILE_STATUS_" not in src, f"{name}: vocabulário de status no controller"
