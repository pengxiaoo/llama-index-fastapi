import unittest
from fastapi.testclient import TestClient
from llama_index.core.llms.types import MessageRole
from app.main import app
from app.data.models.mongodb import Message
from app.data.messages.qa import QuestionAnsweringRequest
from app.tests.test_base import BaseTest


class ChatTest(BaseTest):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_CHAT = "chat"

    def test_non_streaming(self):
        message = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_and_in_knowledge_base"
        ]["question"]
        conversation_id = "1"
        body = {
            "conversation_id": conversation_id,
            "role": "user",
            "content": message,
        }
        response = self.client.post(
            url=f"{self.ROOT}/{self.ROUTER_CHAT}/non-streaming", json=body
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        message = Message(**json_response["data"])
        self.assertEqual(message.role, MessageRole.ASSISTANT)
        self.assertEqual(message.conversation_id, conversation_id)


if __name__ == "__main__":
    unittest.main()
