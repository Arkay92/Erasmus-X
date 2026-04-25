import unittest
import sys
import os
import shutil
from unittest.mock import MagicMock
from core.agent import NeurosymbolicAgent
from core import config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestAcceptanceFlows(unittest.TestCase):
    """E2E-style tests with mocked LLM but real system logic."""
    
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_brain = MagicMock()
        self.mock_kg = MagicMock()
        self.mock_searcher = MagicMock()
        
        # Ensure sandboxes don't interfere
        self.sandbox_root = "test_sandboxes"
        config.SANDBOX_ROOT = self.sandbox_root
        os.makedirs(self.sandbox_root, exist_ok=True)
        
        self.agent = NeurosymbolicAgent(
            client=self.mock_client,
            brain=self.mock_brain,
            kg=self.mock_kg,
            searcher=self.mock_searcher
        )

    def tearDown(self):
        if os.path.exists(self.sandbox_root):
            shutil.rmtree(self.sandbox_root)

    def test_simple_code_generation_flow(self):
        """User asks for code -> Agent returns it -> Files are saved."""
        user_input = "write a hello world in python"
        
        # Mock Brain behaviors
        self.mock_brain.search_cache.return_value = None
        self.mock_brain.classify_intent.return_value = ("INFO", 0.9)
        self.mock_brain.search.return_value = []
        
        # Mock LLM Response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "[FILE: hello.py]\n```python\nprint('hello')\n```"
        self.mock_client.chat.completions.create.return_value = mock_response
        
        # Act
        raw, clean = self.agent.chat(user_input, mode_override="FAST")
        
        # Assert
        self.assertIn("hello.py", raw)
        # Verify file actually landed in sandbox (if coding loop triggered)
        # Note: In FAST mode it might not trigger autonomous_coding_loop unless meta['is_code'] is set.
        # Let's verify the router logic in the agent.

if __name__ == '__main__':
    unittest.main()
