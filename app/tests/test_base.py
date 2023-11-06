import unittest
import time
from fastapi.testclient import TestClient
from app.launch import index_server_main
from app.main import app
from app.data.messages.status_code import StatusCode
from app.data.messages.qa import QuestionAnsweringRequest


class BaseTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER = "qa"
    index_process = None

    def setUp(self):
        self.index_process = index_server_main()
        time.sleep(10)

    def tearDown(self) -> None:
        self.index_process.terminate()

    def test_ask_questions(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_not_relevant"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        json_dict = response.json()
        self.assertEqual(
            json_dict["status_code"], StatusCode.SUCCEEDED, f"response: {json_dict}"
        )
