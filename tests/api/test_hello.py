"""Testes TDD da feature F-002 (FastAPI hello world).

Valida AC-001/AC-002: app FastAPI com GET / retornando hello world.
"""

import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class TestHelloWorld(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_ac001_get_root_returns_200(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_ac002_get_root_returns_hello_json(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.json(), {"message": "Hello World"})
        self.assertEqual(resp.headers["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()