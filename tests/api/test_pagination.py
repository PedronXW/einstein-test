"""Testes TDD da feature F-036 (paginação nos endpoints de listagem).

Valida AC-001..AC-005 via TestClient: envelope paginado nos 3 endpoints de
listagem, defaults, total_pages e validação 422 dos parâmetros.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.models.chat import Chat
from einstein_test.models.file import File
from einstein_test.models.message import Message
from tests.conftest import register_and_login


@pytest.fixture
def ctx():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from einstein_test.api.dependencies import configure_session_factory

    configure_session_factory(engine)

    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        headers = register_and_login(c, email="user@b.com")
        user_id = c.get("/users/me", headers=headers).json()["id"]
        yield c, headers, engine, user_id
    engine.dispose()


def _seed_chats(engine, user_id, n, base_hour=0):
    with Session(engine) as s:
        for i in range(n):
            s.add(Chat(
                user_id=user_id,
                name=f"chat-{i:02d}",
                description=None,
                created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=base_hour + i),
            ))
        s.commit()


def _seed_messages(engine, chat_id, n, base_hour=0):
    with Session(engine) as s:
        for i in range(n):
            s.add(Message(
                chat_id=chat_id,
                content=f"msg-{i:02d}",
                role="user",
                created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=base_hour + i),
            ))
        s.commit()


def _seed_files(engine, chat_id, n, base_hour=0):
    with Session(engine) as s:
        for i in range(n):
            s.add(File(
                chat_id=chat_id,
                name=f"file-{i:02d}.txt",
                url=f"s3://einstein/file-{i:02d}.txt",
                size=i,
                created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=base_hour + i),
            ))
        s.commit()


def _assert_envelope(body, items, page, page_size, total, total_pages):
    assert set(body.keys()) == {"items", "page", "page_size", "total", "total_pages"}
    assert body["page"] == page
    assert body["page_size"] == page_size
    assert body["total"] == total
    assert body["total_pages"] == total_pages
    assert len(body["items"]) == items


def test_ac001_list_chats_paginated(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 25)

    resp = client.get("/chats", params={"page": 1, "page_size": 10}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=10, page=1, page_size=10, total=25, total_pages=3)
    names = [c["name"] for c in body["items"]]
    assert names == [f"chat-{i:02d}" for i in range(24, 14, -1)], (
        "chats ordenados por created_at desc (mais recente primeiro)"
    )


def test_ac001_list_chats_last_page(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 25)

    resp = client.get("/chats", params={"page": 3, "page_size": 10}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=5, page=3, page_size=10, total=25, total_pages=3)


def test_ac002_list_messages_paginated(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "chat-msg"}, headers=headers).json()
    _seed_messages(engine, chat["id"], 15)

    resp = client.get(
        f"/chats/{chat['id']}/messages",
        params={"page": 2, "page_size": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=5, page=2, page_size=5, total=15, total_pages=3)
    contents = [m["content"] for m in body["items"]]
    assert contents == [f"msg-{i:02d}" for i in range(5, 10)], (
        "mensagens em ordem ascendente (cronológica) estável"
    )


def test_ac003_list_files_paginated(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "chat-file"}, headers=headers).json()
    _seed_files(engine, chat["id"], 7)

    resp = client.get(
        f"/chats/{chat['id']}/files",
        params={"page": 1, "page_size": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=3, page=1, page_size=3, total=7, total_pages=3)
    names = [f["name"] for f in body["items"]]
    assert names == [f"file-{i:02d}.txt" for i in range(6, 3, -1)], (
        "files ordenados por created_at desc"
    )


def test_ac004_defaults_page_one_page_size_20(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 5)

    resp = client.get("/chats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=5, page=1, page_size=20, total=5, total_pages=1)


def test_ac004_empty_total_pages_zero(ctx):
    client, headers, engine, user_id = ctx

    resp = client.get("/chats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=0, page=1, page_size=20, total=0, total_pages=0)


def test_ac004_page_beyond_end_returns_empty_items(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 5)

    resp = client.get("/chats", params={"page": 99}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=0, page=99, page_size=20, total=5, total_pages=1)


def test_ac005_validation_422(ctx):
    client, headers, engine, user_id = ctx

    assert client.get("/chats", params={"page": 0}, headers=headers).status_code == 422
    assert client.get("/chats", params={"page_size": 0}, headers=headers).status_code == 422
    assert client.get("/chats", params={"page_size": 101}, headers=headers).status_code == 422
    assert client.get(
        "/chats", params={"page_size": "abc"}, headers=headers
    ).status_code == 422


def test_ac005_page_size_100_ok(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 3)

    resp = client.get("/chats", params={"page_size": 100}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["page_size"] == 100


def test_ac001_chats_same_timestamp_order_by_id_desc(ctx):
    client, headers, engine, user_id = ctx
    with Session(engine) as s:
        for i in range(3):
            s.add(Chat(
                user_id=user_id,
                name=f"tie-{i:02d}",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ))
        s.commit()
    resp = client.get("/chats", params={"page_size": 100}, headers=headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["items"]]
    assert names == ["tie-02", "tie-01", "tie-00"], (
        "created_at igual -> desempate por id desc (estabilidade)"
    )


def test_ac002_messages_same_timestamp_order_by_id_asc(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "tie-msg"}, headers=headers).json()
    with Session(engine) as s:
        for i in range(3):
            s.add(Message(
                chat_id=chat["id"],
                content=f"tie-{i:02d}",
                role="user",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ))
        s.commit()
    resp = client.get(
        f"/chats/{chat['id']}/messages",
        params={"page_size": 100},
        headers=headers,
    )
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()["items"]]
    assert contents == ["tie-00", "tie-01", "tie-02"], (
        "created_at igual -> desempate por id asc (estabilidade)"
    )


def test_ac003_files_same_timestamp_order_by_id_desc(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "tie-file"}, headers=headers).json()
    with Session(engine) as s:
        for i in range(3):
            s.add(File(
                chat_id=chat["id"],
                name=f"tie-{i:02d}.txt",
                url=f"s3://einstein/tie-{i:02d}.txt",
                size=i,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            ))
        s.commit()
    resp = client.get(
        f"/chats/{chat['id']}/files",
        params={"page_size": 100},
        headers=headers,
    )
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()["items"]]
    assert names == ["tie-02.txt", "tie-01.txt", "tie-00.txt"], (
        "created_at igual -> desempate por id desc (estabilidade)"
    )


def test_ac001_chats_paginated_isolated_between_users(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 3)
    other = register_and_login(client, email="outro@b.com")

    resp = client.get("/chats", params={"page": 1, "page_size": 10}, headers=other)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=0, page=1, page_size=10, total=0, total_pages=0)


def test_ac002_messages_paginated_404_for_other_user_chat(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "de-a"}, headers=headers).json()
    _seed_messages(engine, chat["id"], 3)
    other = register_and_login(client, email="outro2@b.com")

    resp = client.get(
        f"/chats/{chat['id']}/messages",
        params={"page": 1, "page_size": 5},
        headers=other,
    )
    assert resp.status_code == 404, "chat alheio nao vaza mensagens (nem total)"


def test_ac003_files_paginated_404_for_other_user_chat(ctx):
    client, headers, engine, user_id = ctx
    chat = client.post("/chats", json={"name": "de-a-file"}, headers=headers).json()
    _seed_files(engine, chat["id"], 3)
    other = register_and_login(client, email="outro3@b.com")

    resp = client.get(
        f"/chats/{chat['id']}/files",
        params={"page": 1, "page_size": 5},
        headers=other,
    )
    assert resp.status_code == 404, "chat alheio nao vaza arquivos (nem total)"


def test_ac002_messages_paginated_404_nonexistent_chat(ctx):
    client, headers, engine, user_id = ctx
    resp = client.get(
        "/chats/999999/messages",
        params={"page": 1, "page_size": 5},
        headers=headers,
    )
    assert resp.status_code == 404


def test_ac003_files_paginated_404_nonexistent_chat(ctx):
    client, headers, engine, user_id = ctx
    resp = client.get(
        "/chats/999999/files",
        params={"page": 1, "page_size": 5},
        headers=headers,
    )
    assert resp.status_code == 404


def test_ac004_soft_deleted_excluded_from_total(ctx):
    client, headers, engine, user_id = ctx
    _seed_chats(engine, user_id, 2)
    with Session(engine) as s:
        chat = s.query(Chat).filter(Chat.user_id == user_id).first()
        chat.deleted_at = datetime(2026, 1, 1, tzinfo=UTC)
        s.commit()

    resp = client.get("/chats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    _assert_envelope(body, items=1, page=1, page_size=20, total=1, total_pages=1)