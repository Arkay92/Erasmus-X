import unittest
import sys
import os
from unittest.mock import MagicMock
from core.agent import NeurosymbolicAgent
from core import config

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestMultiAgentAndDistiller(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_brain = MagicMock()
        self.mock_kg = MagicMock()
        self.mock_searcher = MagicMock()
        
        # Mock Local LLM (Erasmus X Substitute)
        self.mock_local_llm = MagicMock()
        self.mock_brain.local_llm = self.mock_local_llm
        
        # Mock Brain behaviors
        self.mock_brain.search_cache.return_value = None
        self.mock_brain.classify_intent.return_value = ("PROJECT", 0.9)
        self.mock_brain.search.return_value = []
        
        self.agent = NeurosymbolicAgent(
            client=self.mock_client,
            brain=self.mock_brain,
            kg=self.mock_kg,
            searcher=self.mock_searcher
        )
        self.agent.local_llm = self.mock_local_llm
        self.agent.prompt_distiller.local_llm = self.mock_local_llm
        self.agent.router.local_llm = self.mock_local_llm

    def test_erasmus_distiller_injection(self):
        """Verify that Erasmus X distillation output is injected into the prompt."""
        user_input = "Implement a high-performance DB layer"
        
        # Mocks
        self.mock_brain.search_cache.return_value = None
        self.mock_brain.classify_intent.return_value = ("PROJECT", 0.9)
        self.mock_brain.search.return_value = []
        
        # Erasmus X "Fine-Tuning" distillation
        self.mock_local_llm.generate.return_value = "USE_INDEXING: TRUE. MINIMIZE_JOINS: TRUE."
        
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "I will implement this."
        self.mock_client.chat.completions.create.return_value = mock_resp
        
        # Act
        self.agent.chat(user_input)
        
        # Assert: Check if any call contains the distillation (it should be the main chat call)
        found = False
        print(f"Total calls: {len(self.mock_client.chat.completions.create.call_args_list)}")
        for i, call in enumerate(self.mock_client.chat.completions.create.call_args_list):
             sent_messages = call[1]['messages']
             print(f"Call {i} messages: {sent_messages[0]['content'][:100]}...")
             for j, msg in enumerate(sent_messages):
                  if "[SPECULATIVE CONSTRAINTS (Tuned by Erasmus X)]" in msg['content']:
                       print(f"Found distillation in call {i} message {j}")
                       self.assertIn("USE_INDEXING: TRUE", msg['content'])
                       found = True
                       break
             if found: break
        
        self.assertTrue(found, "Distilled constraints were not found in any LLM call.")

    def test_subagent_delegation(self):
        """Verify that the Orchestrator spawns subagents when DELEGATE is chosen by Dispatcher."""
        user_input = "Build a complex app"
        
        self.mock_brain.search.return_value = []
        
        # Mock Router to not force a project
        self.agent.router = MagicMock()
        self.agent.router.route.return_value = {
            'intent': 'INFO',
            'confidence': 0.9,
            'mode': 'DEEP',
            'is_code': False,
            'is_project': False,
            'is_dynamic': False
        }
        
        # Mock Dispatcher to choose DELEGATE
        self.agent.dispatcher = MagicMock()
        self.agent.dispatcher.select_action.return_value = {
            "operation": "DELEGATE",
            "thought": "This task is too big, breaking it down.",
            "payload": {
                "delegations": [
                    {"role": "UI", "task": "Design the login page"},
                    {"role": "Backend", "task": "Create the login API"}
                ]
            }
        }
        
        subagent_ui_resp = MagicMock()
        subagent_ui_resp.choices[0].message.content = "UI Complete."
        
        subagent_be_resp = MagicMock()
        subagent_be_resp.choices[0].message.content = "Backend Complete."
        
        self.mock_client.chat.completions.create.side_effect = [subagent_ui_resp, subagent_be_resp]
        
        # Act
        raw, clean = self.agent.chat(user_input, mode_override="DEEP")
        print(f"DEBUG raw: {raw}")
        print(f"DEBUG clean: {clean}")
        
        # Assert
        self.assertIn("- UI: UI Complete.", raw)
        self.assertIn("- Backend: Backend Complete.", raw)

if __name__ == '__main__':
    unittest.main()
