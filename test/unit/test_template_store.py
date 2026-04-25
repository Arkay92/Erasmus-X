
import unittest
import sys
import os
import json
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.template_store import get_best_skeleton, get_best_skeleton_from_brain, TEMPLATE_MAP

class TestTemplateStoreDeep(unittest.TestCase):
    def setUp(self):
        self.mock_brain = MagicMock()
        
    def test_deterministic_retrieval_priorities(self):
        """Verify that deterministic templates match correctly for various paths."""
        # Next.js Layout
        self.assertEqual(get_best_skeleton("app/layout.tsx")['path'], "app/layout.tsx")
        self.assertEqual(get_best_skeleton("src/app/layout.js")['path'], "app/layout.tsx")
        
        # Next.js Page
        self.assertEqual(get_best_skeleton("app/dashboard/page.tsx")['path'], "app/page.tsx")
        
        # Manifests
        self.assertEqual(get_best_skeleton("package.json")['path'], "package.json")
        
        # Python
        self.assertEqual(get_best_skeleton("core/__init__.py")['path'], "__init__.py")
        
        # Fallbacks
        self.assertEqual(get_best_skeleton("app/api/auth/route.ts")['content'], TEMPLATE_MAP['nextjs_generic_api']['content'])
        self.assertEqual(get_best_skeleton("components/Button.tsx")['content'], TEMPLATE_MAP['nextjs_generic_component']['content'])
        self.assertEqual(get_best_skeleton("lib/utils.ts")['content'], TEMPLATE_MAP['nextjs_generic_ts']['content'])

    def test_brain_lookup_triggers(self):
        """Verify that specific signals trigger the brain lookup."""
        # 1. Trigger for 'db'
        # Note: In the real brain, search results are [(score, doc), ...]
        self.mock_brain.search.return_value = [
            (0.9, '[FEATURE_PACK] FEATURE: db | STACK: nextjs | CONTENT: {"feature": "db", "content": "FINAL_FALLBACK", "files": [{"path": "lib/db.brain", "content": "PRISMA_CODE"}]}')
        ]
        
        # Using .brain to avoid deterministic TS fallback match for verification
        skel = get_best_skeleton("lib/db.brain", brain=self.mock_brain)
        self.assertIsNotNone(skel, "Skeleton should not be None for lib/db.brain")
        self.assertEqual(skel['content'], "PRISMA_CODE")

        # Reset mock
        self.mock_brain.search.reset_mock()
        
        # 2. Trigger for 'auth'
        self.mock_brain.search.return_value = [
            (0.9, '[FEATURE_PACK] FEATURE: auth | STACK: nextjs | CONTENT: {"feature": "auth", "content": "AUTH_FALLBACK", "files": [{"path": "app/login/page.brain", "content": "AUTH_CODE"}]}')
        ]
        skel = get_best_skeleton("app/login/page.brain", brain=self.mock_brain)
        self.assertIsNotNone(skel, "Skeleton should not be None for app/login/page.brain")
        self.assertEqual(skel['content'], "AUTH_CODE")

    def test_brain_lookup_failure_fallback(self):
        """Verify fallback when brain search succeeds but parsing or matching fails."""
        # Return junk document
        self.mock_brain.search.return_value = [(0.9, "I am just a random text")]
        
        # Should fall back to generic TS since it's a .ts file
        skel = get_best_skeleton("lib/db.ts", brain=self.mock_brain)
        self.assertEqual(skel['content'], TEMPLATE_MAP['nextjs_generic_ts']['content'])

    def test_brain_signal_mapping(self):
        """Verify various signals map to the correct feature names."""
        self.mock_brain.search.return_value = []
        
        # List of (filename, expected_feature_in_query)
        test_cases = [
            ("database.py", "db"),
            ("prisma_db.ts", "db"),
            ("user_dashboard.tsx", "dashboard"),
            ("auth_provider.tsx", "auth"),
            ("login_form.js", "auth")
        ]
        
        for fname, feat in test_cases:
            get_best_skeleton(fname, brain=self.mock_brain)
            # Last call search query check
            last_query = self.mock_brain.search.call_args[0][0]
            self.assertIn(f"FEATURE: {feat}", last_query)

if __name__ == '__main__':
    unittest.main()
