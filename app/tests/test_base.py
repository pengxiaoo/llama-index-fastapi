import unittest
from fastapi.testclient import TestClient
import base64
from app.main import app
from app.data.messages.qa import (
    QuestionAnsweringRequest,
    QuestionAnsweringResponse,
    DocumentRequest,
    DocumentResponse,
)
from app.data.models.qa import Source, get_default_answer
from app.utils import data_consts


class BaseTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_QA = "qa"
    ROUTER_ADMIN = "admin"

    @staticmethod
    def create_authorization_header(username: str, password: str) -> dict:
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}

    def setUp(self):
        self.doc_id = None
        auth_header = self.create_authorization_header(data_consts.EXPECTED_USERNAME, data_consts.EXPECTED_PASSWORD)
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_ADMIN}/cleanup", headers=auth_header)
        self.assertEqual(response.status_code, 200)

    def delete_doc(self, doc_id):
        response = self.client.delete(url=f"{self.ROOT}/{self.ROUTER_ADMIN}/documents/{doc_id}")
        self.assertEqual(response.status_code, 200)

    def _tearDown(self):
        if self.doc_id:
            self.delete_doc(self.doc_id)

    def check_document(self, doc_id, from_knowledge_base):
        data = DocumentRequest.ConfigDict.json_schema_extra
        data["doc_id"] = doc_id
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_QA}/document", json=data)
        response = DocumentResponse(**response.json())
        self.assertIsNotNone(response.data)
        if from_knowledge_base:
            self.assertTrue(response.data.source == Source.KNOWLEDGE_BASE)
        else:
            self.assertTrue(response.data.source != Source.KNOWLEDGE_BASE)

    def test_ask_questions_not_relevant(self):
        data = QuestionAnsweringRequest.ConfigDict.json_schema_extra[
            "example_not_relevant"
        ]
        response = self.client.post(url=f"{self.ROOT}/{self.ROUTER_QA}/query", json=data)
        response = QuestionAnsweringResponse(**response.json())
        self.assertEqual(response.data.answer, get_default_answer())
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
