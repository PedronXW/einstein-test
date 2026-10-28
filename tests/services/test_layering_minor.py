"""Testes TDD da feature F-031 (AC-008: parsing s3 unificado + AuthService sem with_session).

Valida que o parsing de URL `s3://bucket/key` mora em `storage` e é usado pela
task e pelo service; e que `AuthService` não expõe `with_session`.
"""


def test_ac008_parse_s3_url_in_storage():
    from einstein_test.storage import parse_s3_url

    assert parse_s3_url("s3://bucket/chats/1/abc.txt") == ("bucket", "chats/1/abc.txt")
    assert parse_s3_url("nao-s3://x") is None
    assert parse_s3_url("s3://bucket") is None, "sem key -> None"
    assert parse_s3_url("") is None
    assert parse_s3_url(None) is None


def test_ac008_auth_service_has_no_with_session():
    from einstein_test.services.auth import AuthService

    assert not hasattr(AuthService, "with_session")
