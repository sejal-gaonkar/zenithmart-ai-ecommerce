"""Integration tests for the current ZenithMart FastAPI application.

The chatbot is mocked so the suite does not call the live Gemini API.
"""

import os
import unittest
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from fastapi.testclient import TestClient
import database
from main import app


class TestZenithMartAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        database.init_db()
        self.session_id = f"api-{uuid4()}"

    def tearDown(self):
        database.clear_session(self.session_id)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("model", data)
        self.assertIn("api_key_loaded", data)

    def test_storefront_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))

    @patch("main.bot_engine.generate_response")
    def test_chat_endpoint_returns_engine_response(self, mock_generate):
        mock_generate.return_value = {
            "response": "Standard shipping takes 3-5 business days.",
            "session_id": self.session_id,
            "latency_ms": 125.5,
            "status": "success",
            "tokens": {"prompt": 100, "completion": 20, "total": 120},
        }
        response = self.client.post(
            "/api/chat",
            json={"message": "How long does shipping take?", "session_id": self.session_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("3-5 business days", response.json()["response"])
        mock_generate.assert_called_once_with(
            self.session_id, "How long does shipping take?"
        )

    def test_chat_rejects_messages_over_max_length(self):
        response = self.client.post(
            "/api/chat",
            json={"message": "x" * 1001, "session_id": self.session_id},
        )
        self.assertEqual(response.status_code, 422)

    def test_history_and_clear_endpoints(self):
        database.log_interaction(
            session_id=self.session_id,
            user_message="Hello",
            bot_response="Welcome to ZenithMart.",
            response_time_ms=100.0,
            status="success",
        )
        history = self.client.get(f"/api/history/{self.session_id}")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["history"]), 1)

        cleared = self.client.post("/api/clear", json={"session_id": self.session_id})
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.json()["status"], "cleared")

        history_after = self.client.get(f"/api/history/{self.session_id}")
        self.assertEqual(history_after.json()["history"], [])

    def test_demo_product_endpoint(self):
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
