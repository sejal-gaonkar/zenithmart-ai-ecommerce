"""
test_api.py - Direct Async Endpoint & Integration Tests for FastAPI AuraStyle Backend
Uses IsolatedAsyncioTestCase for robust native async testing without event loop conflicts.
"""

import os
os.environ["OPENAI_API_KEY"] = "test-mock-key"

import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import json

from main import (
    health_check,
    serve_index,
    chat_endpoint,
    get_history_endpoint,
    clear_session_endpoint,
    get_logs_endpoint,
    get_analytics_endpoint,
    ChatRequest,
    ClearSessionRequest,
)
import database

class TestFastAPIEndpoints(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        database.init_db()
        self.session_id = "api_test_session_456"

    async def asyncTearDown(self):
        database.clear_session(self.session_id)

    async def test_health_endpoint(self):
        result = await health_check()
        self.assertEqual(result["status"], "healthy")
        self.assertIn("AuraStyle", result["service"])

    async def test_index_page_serves_html(self):
        response = await serve_index()
        self.assertEqual(response.status_code, 200)
        self.assertIn("AuraStyle Support", response.body.decode("utf-8"))
        self.assertIn("Virtual Assistant Aura", response.body.decode("utf-8"))

    async def test_empty_message_raises_400(self):
        req = ChatRequest(session_id=self.session_id, message="   ")
        with self.assertRaises(HTTPException) as ctx:
            await chat_endpoint(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be empty", ctx.exception.detail)

    @patch("bot_engine.OpenAI")
    async def test_chat_endpoint_success(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "Standard Ground takes 3 to 5 business days and is free on orders $75+."
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 410
        mock_completion.usage.completion_tokens = 20
        mock_completion.usage.total_tokens = 430
        mock_client.chat.completions.create.return_value = mock_completion

        req = ChatRequest(session_id=self.session_id, message="How fast is standard shipping?")
        response = await chat_endpoint(req)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.body.decode("utf-8"))
        self.assertIn("3 to 5 business days", data["response"])
        self.assertIn("latency_ms", data)
        self.assertEqual(data["tokens"]["total"], 430)

    async def test_history_and_clear_endpoints(self):
        database.log_interaction(
            session_id=self.session_id,
            user_message="Hello Aura",
            bot_response="Hello! Welcome to AuraStyle Essentials.",
            response_time_ms=120.0,
            status="success"
        )

        hist_data = await get_history_endpoint(self.session_id)
        self.assertEqual(len(hist_data["history"]), 1)
        self.assertEqual(hist_data["history"][0]["user_message"], "Hello Aura")

        clear_data = await clear_session_endpoint(ClearSessionRequest(session_id=self.session_id))
        self.assertEqual(clear_data["status"], "success")

        hist_data_after = await get_history_endpoint(self.session_id)
        self.assertEqual(len(hist_data_after["history"]), 0)

    async def test_logs_and_analytics_endpoints(self):
        logs_data = await get_logs_endpoint(limit=10)
        self.assertIn("logs", logs_data)

        analytics_data = await get_analytics_endpoint()
        self.assertIn("total_messages", analytics_data)
        self.assertIn("avg_latency_ms", analytics_data)

if __name__ == "__main__":
    unittest.main()
