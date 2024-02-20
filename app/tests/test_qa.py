import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.data.messages.qa import (
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
)
from app.data.models.qa import Source, get_default_answer
from app.llama_index_server.chat_message_dao import ChatMessageDao
from app.tests.test_base import BaseTest


class QaTest(BaseTest):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_QA = "qa"
    ROUTER_ADMIN = "admin"
    chat_message_dao = ChatMessageDao()

    def test_ask_questions_not_relevant(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_not_relevant"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_QA}/query", json=data)
        response = QuestionAnsweringResponse(**response.json())
        self.assertEqual(get_default_answer(), response.data.answer)
        self.check_document(doc_id=data["question"], from_knowledge_base=False)
        self.doc_id = data["question"]

    def test_ask_questions_relevant_and_in_knowledge_base(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_and_in_knowledge_base"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_QA}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertNotEqual(response.data.answer, get_default_answer())
        self.assertEqual(response.data.source, Source.KNOWLEDGE_BASE)
        self.assertIsNotNone(response.data.matched_question)
        self.check_document(doc_id=response.data.matched_question, from_knowledge_base=True)
        self.doc_id = response.data.matched_question

    def test_ask_questions_relevant_but_not_in_knowledge_base(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_but_not_in_knowledge_base"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_QA}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertNotEqual(response.data.answer, get_default_answer())
        self.check_document(doc_id=data["question"], from_knowledge_base=False)


if __name__ == "__main__":
    unittest.main()
