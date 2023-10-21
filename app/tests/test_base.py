import unittest
from fastapi.testclient import TestClient
from app.main import app


class BaseTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"

    def setUp(self):
        pass

    def tearDown(self) -> None:
        pass
