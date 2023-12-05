import unittest
import time
from fastapi.testclient import TestClient
from app.launch import index_server_main
from app.main import app
from app.data.messages.response import ANSWER_TO_IRRELEVANT_QUESTION
from app.data.messages.status_code import StatusCode
from app.data.messages.qa import QuestionAnsweringRequest, QuestionAnsweringResponse
from app.data.models.qa import Source


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

    def test_ask_questions_not_relevant(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_not_relevant"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertEqual(
            response.status_code, StatusCode.SUCCEEDED, f"response: {json_dict}"
        )
        self.assertEqual(response.data.answer, ANSWER_TO_IRRELEVANT_QUESTION)
        self.assertEqual(response.data.source, Source.CHATGPT35)

    def test_ask_questions_relevant_and_in_database(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_and_in_database"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertEqual(
            response.status_code, StatusCode.SUCCEEDED, f"response: {json_dict}"
        )
        self.assertNotEqual(response.data.answer, ANSWER_TO_IRRELEVANT_QUESTION)
        self.assertEqual(response.data.source, Source.KNOWLEDGE_BASE)

    def test_ask_questions_relevant_but_not_in_database(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_but_not_in_database"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertEqual(
            response.status_code, StatusCode.SUCCEEDED, f"response: {json_dict}"
        )
        self.assertNotEqual(response.data.answer, ANSWER_TO_IRRELEVANT_QUESTION)
        self.assertEqual(response.data.source, Source.CHATGPT35)


if __name__ == "__main__":
    unittest.main()
