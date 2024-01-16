import unittest
from fastapi.testclient import TestClient

from app.main import app


class ChatTest(unittest.TestCase):
    client = TestClient(app=app)
    ROOT = "/api/v1"
    ROUTER_CHAT = "chat"


    def test_dialog(self):
        message = "How many players in table tennis game?"
        body = {
            "conversation_id": "1",
            "orignator": "user",
            "dialog": message,
            "sequence_num": 0
        }

        response = self.client.post(
            url=f"{self.ROOT}/{self.ROUTER_CHAT}/dialog", json=body
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response["data"]["message"], message)


if __name__ == "__main__":
    unittest.main()