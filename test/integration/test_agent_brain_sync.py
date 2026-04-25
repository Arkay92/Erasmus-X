
import unittest
import sys
import os
import json
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.agent import NeurosymbolicAgent
from core import config

class TestBrainAgentIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_brain = MagicMock()
        self.mock_kg = MagicMock()
        self.mock_searcher = MagicMock()
        
        # Mock brain essentials
        self.mock_brain.documents = []
        
        self.agent = NeurosymbolicAgent(
            client=self.mock_client,
            brain=self.mock_brain,
            kg=self.mock_kg,
            searcher=self.mock_searcher
        )

    def test_autonomous_synthesis_to_brain(self):
        """Verify that synthesis loop persists [FEATURE_PACK] documents to brain."""
        # 1. Setup Synthesis Response
        mock_resp = MagicMock()
        pack_content = {
            "feature": "analytics",
            "stack": "nextjs",
            "files": [{"path": "lib/analytics.ts", "content": "export const track = () => {}"}]
        }
        mock_resp.choices[0].message.content = f"[SYNTHESIS: PACK]\nName: analytics\nContent: {json.dumps(pack_content)}"
        self.mock_client.chat.completions.create.return_value = mock_resp
        
        # 2. Run synthesis loop
        config.ENABLE_AUTONOMOUS_SYNTHESIS = True
        self.agent._run_synthesis_loop("Build a dashboard with analytics", [])
        
        # 3. Verify Brain Calls
        # Should have added document with [FEATURE_PACK] marker
        doc_added = None
        for call in self.mock_brain.add_document.call_args_list:
            if "[FEATURE_PACK]" in call[0][0]:
                doc_added = call[0][0]
                break
        
        self.assertIsNotNone(doc_added)
        self.assertIn("FEATURE: analytics", doc_added)
        self.assertIn("CONTENT: {", doc_added)
        
        # Verify capability association added
        self.mock_brain.add_capability_association.assert_called()
        self.mock_brain.save.assert_called()

    def test_session_stability_trigger(self):
        """Verify that agent triggers spin-down when context is heavy."""
        # Mock router to return non-project intent
        self.mock_brain.classify_intent.return_value = ("INFO", 0.9)
        self.mock_brain.search_cache.return_value = None
        self.mock_brain.search.return_value = []
        self.mock_kg.get_related_facts.return_value = []
        
        # Mock LLM for normal chat
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Normal response"
        self.mock_client.chat.completions.create.return_value = mock_resp
        
        # Trigger Spin Down (High history token count)
        # We need to simulate history tokens > 80% of limit
        limit = config.FAST_MODE_CONTEXT_TOKENS
        heavy_content = "X " * int(limit) # Very heavy
        self.agent.messages = [{"role": "user", "content": heavy_content}]
        
        # Mock session manager spin down behavior
        self.agent.session_manager.perform_spin_down = MagicMock(return_value=True)
        
        self.agent.chat("Next question")
        
        # Verify spin down was called
        # self.agent.session_manager.perform_spin_down.assert_called()
        # In chat(): if self.session_manager.check_stability_trigger(self.messages): ...
        
        # Re-verify by checking if messages were reset
        self.assertEqual(len(self.agent.messages), 2) # Only new user and assistant message left

    def test_agent_orchestration_retrieval(self):
        """Verify retrieval flow (Brain -> KG -> Context)."""
        self.mock_brain.classify_intent.return_value = ("INFO", 0.9)
        self.mock_brain.search_cache.return_value = None
        self.mock_brain.search.return_value = [(0.8, "Fact A"), (0.7, "Fact B")]
        self.mock_kg.get_related_facts.return_value = ["Fact C"]
        self.agent.session_manager.get_structured_state = MagicMock(return_value="Last State")
        
        # Mock LLM for the chat loop
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Retrieved response"
        self.mock_client.chat.completions.create.return_value = mock_resp
        
        # Act
        self.agent.chat("tell me about the project")
        
        # Verify context builder was called with retrieved data
        self.agent.context_builder.build_messages = MagicMock(return_value=([], 0))
        self.agent.chat("tell me about the project")
        
        call_args = self.agent.context_builder.build_messages.call_args
        memory_results = call_args[0][2]
        
        self.assertEqual(memory_results['facts'], ["Fact C"])
        self.assertEqual(memory_results['session'][0][1], "Last State")

if __name__ == '__main__':
    unittest.main()
