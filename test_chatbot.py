"""Unit tests for the ZenithMart Gemini chatbot engine.

These tests mock the Gemini-compatible OpenAI client. They do not make paid
network requests and do not prove that a real API key is valid.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

import database
from bot_engine import (
    ChatbotEngine,
    build_system_prompt,
    knowledge_loader,
    session_manager,
)


class TestZenithMartChatbot(unittest.TestCase):
    def setUp(self):
        database.init_db()
        self.session_id = f"unit-{uuid4()}"

    def tearDown(self):
        session_manager.clear(self.session_id)

    def test_knowledge_file_loads_zenithmart_policies(self):
        content = knowledge_loader.get_content(reload=True)
        self.assertIn("ZenithMart", content)
        self.assertIn("3-5 business days", content)
        self.assertIn("Rs 49", content)
        self.assertIn("support@zenithmart.example", content)

    def test_system_prompt_has_four_layers_and_correct_brand(self):
        prompt = build_system_prompt()
        self.assertIn('You are "Aura"', prompt)
        self.assertIn("ZenithMart", prompt)
        for layer in (
            "LAYER 1: PERSONA & COMMUNICATION STYLE",
            "LAYER 2: OFFICIAL DOMAIN KNOWLEDGE BASE",
            "LAYER 3: STRICT SCOPE CONTROL & REFUSAL POLICY",
            "LAYER 4: SAFETY, HONESTY & ESCALATION",
        ):
            self.assertIn(layer, prompt)
        self.assertNotIn("AuraStyle", prompt)

    def test_empty_input_does_not_call_gemini(self):
        engine = ChatbotEngine()
        with patch.object(engine, "_get_client") as client_factory:
            result = engine.generate_response(self.session_id, "   ")
        self.assertEqual(result["status"], "empty_input")
        self.assertIn("Please enter a message", result["response"])
        client_factory.assert_not_called()

    def test_missing_api_key_returns_gemini_error(self):
        engine = ChatbotEngine()
        engine.api_key = ""
        result = engine.generate_response(self.session_id, "What is shipping?")
        self.assertEqual(result["status"], "gemini_error")
        self.assertIn("Gemini", result["response"])
        logs = database.get_session_history(self.session_id)
        self.assertEqual(logs[-1]["status"], "gemini_error")

    @patch("bot_engine.OpenAI")
    def test_successful_gemini_response_is_logged(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        choice = MagicMock()
        choice.message.content = "Standard shipping takes 3-5 business days."
        completion = MagicMock()
        completion.choices = [choice]
        completion.usage.prompt_tokens = 100
        completion.usage.completion_tokens = 20
        completion.usage.total_tokens = 120
        mock_client.chat.completions.create.return_value = completion

        engine = ChatbotEngine()
        engine.api_key = "test-gemini-key"
        result = engine.generate_response(self.session_id, "How long is standard shipping?")

        self.assertEqual(result["status"], "success")
        self.assertIn("3-5 business days", result["response"])
        self.assertEqual(result["tokens"]["total"], 120)
        mock_client.chat.completions.create.assert_called_once()
        logs = database.get_session_history(self.session_id)
        self.assertEqual(logs[-1]["status"], "success")

    def test_session_manager_keeps_recent_turns(self):
        session_manager.append_turn(self.session_id, "Hello", "Welcome to ZenithMart.")
        session_manager.append_turn(self.session_id, "Shipping?", "Standard takes 3-5 days.")
        history = session_manager.get_history(self.session_id)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[-1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
