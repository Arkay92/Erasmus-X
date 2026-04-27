import unittest
import sys
import os
from unittest.mock import MagicMock

# project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.router import TaskRouter
from core.context_builder import ContextBuilder
from core.reasoning_engine import ReasoningEngine
from core import config

class TestErasmusStages(unittest.TestCase):
    def setUp(self):
        self.mock_brain = MagicMock()
        self.mock_client = MagicMock()
        self.mock_local_llm = MagicMock()
        self.router = TaskRouter(brain=self.mock_brain, local_llm=self.mock_local_llm)

    def test_router_logic(self):
        """Verify routing intent classification."""
        self.mock_brain.classify_intent.return_value = ("PROJECT", 0.9)
        query = "Create a new Next.js project with authentication"
        meta = self.router.route(query)
        self.assertEqual(meta['mode'], 'DEEP')
        self.assertEqual(meta['intent'], 'PROJECT')

        self.mock_brain.classify_intent.return_value = ("RECALL", 0.2)
        meta = self.router.route("Build me a bot in PHP with tests and a webhook endpoint")
        self.assertTrue(meta['is_project'])
        self.assertEqual(meta['language'], "php")

    def test_context_budgeting(self):
        """Verify context builder correctly handles token limits."""
        builder = ContextBuilder()
        user_input = "Hello"
        history = [{"role": "user", "content": "Hi"}]
        memory_results = {'session': [], 'facts': [], 'web': None}
        
        messages, tokens = builder.build_messages(user_input, history, memory_results, mode="FAST")
        self.assertLessEqual(tokens, config.FAST_MODE_CONTEXT_TOKENS)

    def test_reasoning_extraction(self):
        """Verify reasoning engine extracts lessons from assistant content."""
        engine = ReasoningEngine(self.mock_client)
        user_input = "test"
        # Mock CoT
        messages = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "[Goal]\nTest\n[Action]\nDo nothing\n[Next]\nDone"}
        ]
        
        # Mock LLM response for analysis
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "REASONING_QUALITY: 90\nLEARNED_LESSON: Always test."
        self.mock_client.chat.completions.create.return_value = mock_resp
        
        engine.analyze_task(user_input, messages, "SUCCESS")
        self.assertTrue(any("Always test" in l['lesson'] for l in engine.lessons))

if __name__ == '__main__':
    unittest.main()
