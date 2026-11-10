"""
test_chatbot.py - Comprehensive Automated Test Suite
Systematically evaluates the 4 customization layers and 10 mandatory requirements:
  1. Persona & Tone
  2. Custom Knowledge Loading
  3. Scope Control & Refusal Policy
  4. Safety & "I Don't Know" Honesty Rules
  5. Conversation Memory Persistence
  6. SQLite Database Logging, Latency, and Analytics
  7. API Error Handling (Auth, Rate Limits, Timeouts)
  8. Empty Input Validation
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Point to local sqlite test db or ensure clean state
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-mock-key")

import database
from bot_engine import (
    knowledge_loader,
    build_system_prompt,
    session_manager,
    bot_engine,
    ChatbotEngine,
)
from openai import AuthenticationError, RateLimitError, APITimeoutError

class TestAuraStyleChatbot(unittest.TestCase):

    def setUp(self):
        database.init_db()
        self.test_session_id = f"test_sess_{datetime.now().timestamp()}"

    def tearDown(self):
        database.clear_session(self.test_session_id)
        session_manager.clear(self.test_session_id)

    # ----------------------------------------------------
    # REQUIREMENT 4: Custom Knowledge Base Verification
    # ----------------------------------------------------
    def test_custom_knowledge_file_loaded(self):
        """Verifies knowledge base exists, is loaded from file, and has substantial domain depth (2-3+ pages)."""
        content = knowledge_loader.get_content()
        self.assertIsNotNone(content)
        self.assertGreater(len(content), 1500, "Knowledge base should contain at least 2-3 pages of content.")
        
        # Check critical e-commerce domain topics are covered
        required_topics = [
            "AuraStyle Essentials",
            "Order Confirmation",
            "30 calendar days",
            "$5.99",
            "Standard Ground",
            "AuraClub",
            "1-Year Limited Warranty",
            "support@aurastyle.com",
            "1-800-555-AURA"
        ]
        for topic in required_topics:
            self.assertIn(topic, content, f"Missing critical domain topic: {topic}")

    # ----------------------------------------------------
    # REQUIREMENT 3: System Prompt 4-Layer Architecture
    # ----------------------------------------------------
    def test_system_prompt_structure(self):
        """Verifies system prompt incorporates all 4 customization layers."""
        prompt = build_system_prompt()
        
        # Layer 1: Persona
        self.assertIn("Aura", prompt)
        self.assertIn("LAYER 1: PERSONA & COMMUNICATION STYLE", prompt)
        
        # Layer 2: Knowledge Base
        self.assertIn("LAYER 2: OFFICIAL DOMAIN KNOWLEDGE BASE", prompt)
        self.assertIn("AuraStyle Essentials", prompt)
        
        # Layer 3: Scope Control
        self.assertIn("LAYER 3: STRICT SCOPE CONTROL & REFUSAL POLICY", prompt)
        self.assertIn("OUT-OF-SCOPE TOPICS (MUST BE POLITELY DECLINED)", prompt)
        
        # Layer 4: Safety & Honesty Rules
        self.assertIn("LAYER 4: SAFETY, HONESTY & \"I DON'T KNOW\" RULES", prompt)
        self.assertIn("ZERO HALLUCINATION", prompt)
        self.assertIn("HUMAN ESCALATION", prompt)

    # ----------------------------------------------------
    # REQUIREMENT 10: SQLite Database Chat Logging & Latency
    # ----------------------------------------------------
    def test_sqlite_logging_and_metrics(self):
        """Verifies chat logs are saved in SQLite with timestamps, latency, tokens, and status."""
        row_id = database.log_interaction(
            session_id=self.test_session_id,
            user_message="What is the shipping cost?",
            bot_response="Standard ground shipping is $6.95, or FREE on orders over $75.",
            response_time_ms=315.4,
            prompt_tokens=420,
            completion_tokens=25,
            total_tokens=445,
            status="success"
        )
        self.assertIsNotNone(row_id)
        self.assertGreater(row_id, 0)

        # Retrieve session history
        history = database.get_session_history(self.test_session_id)
        self.assertEqual(len(history), 1)
        record = history[0]
        self.assertEqual(record["user_message"], "What is the shipping cost?")
        self.assertEqual(record["response_time_ms"], 315.4)
        self.assertEqual(record["total_tokens"], 445)
        self.assertEqual(record["status"], "success")

        # Check analytics summary
        summary = database.get_analytics_summary()
        self.assertGreaterEqual(summary["total_messages"], 1)
        self.assertGreaterEqual(summary["sum_tokens"], 445)

    # ----------------------------------------------------
    # REQUIREMENT 5: Conversation Memory Persistence
    # ----------------------------------------------------
    def test_conversation_memory(self):
        """Verifies session manager remembers multi-turn context."""
        session_manager.append_turn(
            self.test_session_id,
            "I ordered an Italian Leather Weekender Bag #AS-4921.",
            "I see your order for the Italian Leather Weekender Bag #AS-4921. How can I assist you with it?"
        )
        history = session_manager.get_history(self.test_session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("Weekender Bag", history[0]["content"])
        self.assertEqual(history[1]["role"], "assistant")

        # Append turn 2
        session_manager.append_turn(
            self.test_session_id,
            "Does it come with a warranty?",
            "Yes! All AuraStyle genuine leather bags come with an automatic 1-Year Limited Warranty."
        )
        history_updated = session_manager.get_history(self.test_session_id)
        self.assertEqual(len(history_updated), 4)

    # ----------------------------------------------------
    # REQUIREMENT 8: Input Validation & Error Handling
    # ----------------------------------------------------
    def test_empty_input_handling(self):
        """Verifies empty and whitespace-only inputs are handled gracefully."""
        res_empty = bot_engine.generate_response(self.test_session_id, "")
        self.assertEqual(res_empty["status"], "empty_input")
        self.assertIn("Please enter a message", res_empty["response"])

        res_spaces = bot_engine.generate_response(self.test_session_id, "   ")
        self.assertEqual(res_spaces["status"], "empty_input")

    @patch("bot_engine.OpenAI")
    def test_authentication_error_handling(self, mock_openai_cls):
        """Verifies invalid API key generates clear user message and logs error status in SQLite."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response_mock = MagicMock()
        mock_response_mock.status_code = 401
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            message="Incorrect API key provided",
            response=mock_response_mock,
            body={"error": {"message": "Incorrect API key provided"}}
        )

        test_engine = ChatbotEngine()
        test_engine.api_key = "invalid-key"
        result = test_engine.generate_response(self.test_session_id, "Where is my order?")

        self.assertEqual(result["status"], "auth_error")
        self.assertIn("Authentication Error", result["response"])
        self.assertIn("OPENAI_API_KEY", result["response"])

        # Check logged to SQLite
        logs = database.get_session_history(self.test_session_id)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["status"], "auth_error")

    @patch("bot_engine.OpenAI")
    def test_rate_limit_error_handling(self, mock_openai_cls):
        """Verifies rate limit error is intercepted and translated cleanly."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_resp,
            body={"error": {"message": "Rate limit exceeded"}}
        )

        test_engine = ChatbotEngine()
        result = test_engine.generate_response(self.test_session_id, "Check points")

        self.assertEqual(result["status"], "rate_limit_error")
        self.assertIn("Rate Limit Exceeded", result["response"])

    @patch("bot_engine.OpenAI")
    def test_connection_timeout_handling(self, mock_openai_cls):
        """Verifies connection and timeout errors provide a helpful network guidance response."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            request=MagicMock()
        )

        test_engine = ChatbotEngine()
        result = test_engine.generate_response(self.test_session_id, "Track order")

        self.assertEqual(result["status"], "connection_error")
        self.assertIn("Network Timeout", result["response"])

    # ----------------------------------------------------
    # REQUIREMENTS 6 & 7: Out-of-Scope Refusal & "I Don't Know"
    # ----------------------------------------------------
    @patch("bot_engine.OpenAI")
    def test_out_of_scope_refusal_response(self, mock_openai_cls):
        """Verifies that an out-of-scope question triggers the proper refusal status."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        # Simulate LLM adhering to Layer 3 Scope Control
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "I'm Aura, your dedicated AuraStyle assistant. I can only assist with questions "
            "regarding AuraStyle orders, shipping, returns, and products. I cannot write Python code. "
            "Would you like help with tracking an order, checking return policies, or AuraClub rewards?"
        )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 500
        mock_completion.usage.completion_tokens = 45
        mock_completion.usage.total_tokens = 545
        mock_client.chat.completions.create.return_value = mock_completion

        test_engine = ChatbotEngine()
        result = test_engine.generate_response(self.test_session_id, "Write a Python script for web scraping")

        self.assertEqual(result["status"], "out_of_scope_refusal")
        self.assertIn("I can only assist with", result["response"])

    @patch("bot_engine.OpenAI")
    def test_in_domain_uncovered_honesty(self, mock_openai_cls):
        """Verifies that an uncovered in-domain question produces an honest 'I don't know' reply."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        # Simulate LLM adhering to Layer 4 Zero Hallucination
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "I don't have that specific information in my records regarding custom neon motorcycle helmets. "
            "Please reach out to our customer care team directly at support@aurastyle.com or call 1-800-555-AURA (1-800-555-2872), "
            "and one of our human specialists will be happy to assist you."
        )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 520
        mock_completion.usage.completion_tokens = 50
        mock_completion.usage.total_tokens = 570
        mock_client.chat.completions.create.return_value = mock_completion

        test_engine = ChatbotEngine()
        result = test_engine.generate_response(self.test_session_id, "Do you sell custom neon motorcycle helmets?")

        self.assertEqual(result["status"], "in_domain_uncovered")
        self.assertIn("I don't have that specific information", result["response"])

    @patch("bot_engine.OpenAI")
    def test_in_scope_knowledge_retrieval(self, mock_openai_cls):
        """Verifies in-scope query returns accurate information from knowledge base."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        mock_choice = MagicMock()
        mock_choice.message.content = (
            "AuraStyle offers a 30-calendar-day return window from the verified delivery date. "
            "If you select store credit or exchange, return shipping is 100% FREE (plus a $5 store credit bonus!). "
            "If you request a refund to your original payment method, a flat $5.99 fee is deducted."
        )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 510
        mock_completion.usage.completion_tokens = 60
        mock_completion.usage.total_tokens = 570
        mock_client.chat.completions.create.return_value = mock_completion

        test_engine = ChatbotEngine()
        result = test_engine.generate_response(self.test_session_id, "What is your return policy and fee?")

        self.assertEqual(result["status"], "success")
        self.assertIn("30-calendar-day return window", result["response"])
        self.assertIn("$5.99", result["response"])

if __name__ == "__main__":
    unittest.main()
