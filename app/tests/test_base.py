import unittest
from fastapi.testclient import TestClient
import base64
from app.main import app
from app.data.messages.qa import (
    DocumentRequest,
    DocumentResponse,
)
from app.data.models.qa import Source
from app.utils import data_consts
from app.llama_index_server.chat_message_dao import ChatMessageDao


class BaseTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_QA = "qa"
    ROUTER_ADMIN = "admin"
    chat_message_dao = ChatMessageDao()

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

    def tearDown(self):
        if self.doc_id:
            self.delete_doc(self.doc_id)

    def delete_doc(self, doc_id):
        auth_header = self.create_authorization_header(data_consts.EXPECTED_USERNAME, data_consts.EXPECTED_PASSWORD)
        response = self.client.delete(url=f"{self.ROOT}/{self.ROUTER_ADMIN}/documents/{doc_id}", headers=auth_header)
        self.assertEqual(response.status_code, 200)

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
