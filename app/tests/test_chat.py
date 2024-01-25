import unittest
from fastapi.testclient import TestClient
from llama_index.core.llms.types import MessageRole
from app.main import app
from app.data.models.mongodb import Message
from app.data.messages.qa import QuestionAnsweringRequest
from app.tests.test_base import BaseTest
from app.utils import csv_util


class ChatTest(BaseTest):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_CHAT = "chat"
    CSV_PATH = "../llama_index_server/documents/golf-knowledge-base.csv"

    def setUp(self):
        super().setUp()
        standard_answers = csv_util.load_standard_answers_from_csv(self.CSV_PATH)
        self.standard_answers = {x.question: x.answer for x in standard_answers}

    def tearDown(self):
        super().tearDown()
        self.chat_message_dao.delete_many({"conversation_id": self.conversation_id})

    def test_non_streaming_question_in_knowledge_base(self):
        query = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_and_in_knowledge_base"
        ]["question"]
        self.conversation_id = "test_1"
        body = {
            "conversation_id": self.conversation_id,
            "role": "user",
            "content": query,
        }
        response = self.client.post(
            url=f"{self.ROOT}/{self.ROUTER_CHAT}/non-streaming", json=body
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        message = Message(**json_response["data"])
        self.assertEqual(message.role, MessageRole.ASSISTANT)
        self.assertEqual(message.conversation_id, self.conversation_id)
        self.assertEqual(message.content, self.standard_answers[query])

    def test_non_streaming_chat_history(self):
        self.conversation_id = "test_2"
        body = {
            "conversation_id": self.conversation_id,
            "role": "user",
            "content": "hi, my name is Christopher",
        }
        response = self.client.post(
            url=f"{self.ROOT}/{self.ROUTER_CHAT}/non-streaming", json=body
        )
        self.assertEqual(response.status_code, 200)
        body["content"] = "what is my name?"
        response = self.client.post(
            url=f"{self.ROOT}/{self.ROUTER_CHAT}/non-streaming", json=body
        )
        json_response = response.json()
        self.assertEqual(response.status_code, 200)
        message = Message(**json_response["data"])
        self.assertIn("Christopher", message.content)


if __name__ == "__main__":
    unittest.main()
