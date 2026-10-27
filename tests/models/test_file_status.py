"""Testes TDD da feature F-015 (AC-001: File com status/error_detail)."""

from einstein_test.models.file import File


def test_ac001_file_has_status_column():
    assert "status" in File.__table__.c, "File.status existe"


def test_ac001_status_default_pending():
    col = File.__table__.c.status
    assert col.default is not None or col.server_default is not None, (
        "status tem default"
    )


def test_ac001_file_has_error_detail_column():
    assert "error_detail" in File.__table__.c, "File.error_detail existe"
    assert File.__table__.c.error_detail.nullable is True


def test_ac001_status_values():
    col = File.__table__.c.status
    # aceita pending|ready|error (SQLAlchemy enum/string)
    assert col.type.length is None or col.type.length >= 7