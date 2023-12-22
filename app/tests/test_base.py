import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.data.messages.qa import (
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
    DocumentRequest,
    DocumentResponse,
)
from app.data.models.qa import Source, get_default_answer


class BaseTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER = "qa"

    def setUp(self):
        self.doc_id = None
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/cleanup")
        self.assertEqual(response.status_code, 200)

    def delete_doc(self, doc_id):
        response = self.client.delete(url=f"{self.ROOT}/{self.ROUTER}/documents/{doc_id}")
        self.assertEqual(response.status_code, 200)

    def _tearDown(self):
        if self.doc_id:
            self.delete_doc(self.doc_id)

    def check_document(self, doc_id, from_knowledge_base=None):
        data = DocumentRequest.ConfigDict.json_schema_extra
        data["doc_id"] = doc_id
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/document", json=data)
        response = DocumentResponse(**response.json())
        self.assertIsNotNone(response.data)
        if from_knowledge_base is not None:
            self.assertEqual(response.data.from_knowledge_base, from_knowledge_base)

    def test_ask_questions_not_relevant(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_not_relevant"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        response = QuestionAnsweringResponse(**response.json())
        self.assertEqual(response.data.answer, get_default_answer())
        self.check_document(doc_id=data["question"], from_knowledge_base=False)
        self.doc_id = data["question"]

    def test_ask_questions_relevant_and_in_knowledge_base(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_relevant_and_in_knowledge_base"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
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
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER}/query", json=data)
        json_dict = response.json()
        response = QuestionAnsweringResponse(**json_dict)
        self.assertNotEqual(response.data.answer, get_default_answer())
        self.check_document(doc_id=data["question"], from_knowledge_base=False)


if __name__ == "__main__":
    unittest.main()
