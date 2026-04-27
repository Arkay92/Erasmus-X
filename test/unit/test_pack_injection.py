"""
Tests for pack injection system.
"""
import unittest
import json
from core.pack_injector import PackInjector
from core.vector_store import HypervectorDB


class TestPackInjector(unittest.TestCase):
    """Test pack injection functionality."""
    
    def setUp(self):
        self.brain = HypervectorDB()
        self.injector = PackInjector(self.brain)
    
    def test_prisma_pack_detection(self):
        """Should detect Prisma requirement in contract."""
        contract = {
            'stack': 'nextjs-app-router|prisma|typescript',
            'features': ['database'],
            'critical_files': []
        }
        
        required = self.injector.get_required_packs(contract)
        self.assertIn('prisma', required)
    
    def test_sqlite_pack_detection(self):
        """Should detect SQLite requirement."""
        contract = {
            'stack': 'nextjs-app-router|sqlite|typescript',
            'features': [],
            'critical_files': ['lib/db.ts']
        }
        
        required = self.injector.get_required_packs(contract)
        self.assertIn('db', required)
    
    def test_api_routes_requirement(self):
        """Should detect API routes requirement."""
        contract = {
            'stack': 'nextjs-app-router|typescript',
            'features': [],
            'critical_files': ['app/api/tasks/route.ts']
        }
        
        required = self.injector.get_required_packs(contract)
        self.assertIn('api-routes', required)
    
    def test_contract_coherence_validation(self):
        """Should detect contract-code mismatches."""
        contract = {
            'stack': 'nextjs-app-router|prisma|typescript',
            'critical_files': []
        }
        
        # File map with SQLite instead of Prisma
        file_map = {
            'lib/db.ts': "import Database from 'better-sqlite3';"
        }
        
        is_coherent, violations = self.injector.validate_contract_coherence(contract, file_map)
        self.assertFalse(is_coherent)
        self.assertTrue(len(violations) > 0)
    
    def test_contract_validation_pass(self):
        """Should validate coherent contracts."""
        contract = {
            'stack': 'nextjs-app-router|prisma|typescript',
            'critical_files': []
        }
        
        # Correct Prisma usage
        file_map = {
            'lib/db.ts': "import { PrismaClient } from '@prisma/client';"
        }
        
        is_coherent, violations = self.injector.validate_contract_coherence(contract, file_map)
        self.assertTrue(is_coherent)
        self.assertEqual(len(violations), 0)


class TestStackFidelityEnforcement(unittest.TestCase):
    """Test that stack requirements are enforced."""
    
    def setUp(self):
        self.brain = HypervectorDB()
        self.injector = PackInjector(self.brain)
    
    def test_prisma_cannot_generate_sqlite(self):
        """Contract with Prisma should not generate sqlite code."""
        contract = {
            'stack': 'nextjs-app-router|prisma|typescript',
            'features': ['database'],
            'critical_files': []
        }
        
        file_map = {
            'lib/db.ts': "import Database from 'better-sqlite3';\nconst db = new Database();"
        }
        
        is_coherent, violations = self.injector.validate_contract_coherence(contract, file_map)
        self.assertFalse(is_coherent)
        
        # Check that the violation message is about Prisma requirement
        violation_messages = '\n'.join(v.get('reason', '') if isinstance(v, dict) else str(v) for v in violations)
        self.assertTrue('sqlite' in violation_messages.lower() and 'prisma' in violation_messages.lower())


if __name__ == '__main__':
    unittest.main()
