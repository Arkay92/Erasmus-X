import os
import tempfile
import unittest

from core.auto_pack_builder import AutoPackBuilder
from core.economic_mode import EconomicMode
from core.execution_memory import ExecutionMemory
from core.scaffold_registry import Scaffold, ScaffoldRegistry
from core.swarm_mode import SwarmMode


class FakeBrain:
    def __init__(self):
        self.feature_packs = {}

    def register_feature_pack(self, name, pack):
        self.feature_packs[name] = pack


class TestVNextSystems(unittest.TestCase):
    def test_execution_memory_records_and_retrieves_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = ExecutionMemory(path=os.path.join(tmp, "execution.jsonl"))
            memory.record_build(
                "Build plumber booking business",
                "nextjs-app-router|prisma",
                "project",
                ["app/page.tsx", "test/booking.test.ts"],
                ["npm test"],
                "verified_static",
            )

            matches = memory.retrieve("plumber booking app", "nextjs-app-router")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["data"]["verification_commands"], ["npm test"])

    def test_auto_pack_builder_promotes_verified_scaffold(self):
        brain = FakeBrain()
        scaffold = Scaffold(
            name="crm_scaffold",
            stack="nextjs",
            files={"app/page.tsx": "export default function Page() { return <main />; }", "test/page.test.ts": "test('x', () => {})"},
            verification_commands=["npm test"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            builder = AutoPackBuilder(brain=brain, marketplace_path=os.path.join(tmp, "packs.jsonl"))
            pack = builder.maybe_create_pack("Build a CRM app", scaffold, list(scaffold.files), {})

        self.assertIsNotNone(pack)
        self.assertIn("crm_pack", brain.feature_packs)
        self.assertEqual(brain.feature_packs["crm_pack"]["verification_commands"], ["npm test"])

    def test_economic_mode_detects_sellable_booking_business(self):
        plan = EconomicMode().evaluate("Build me a plumber booking business", ["plumber_booking_pack"])

        self.assertTrue(plan["use_existing_pack"])
        self.assertTrue(plan["should_template"])
        self.assertTrue(plan["sellable_output"])
        self.assertIn("admin dashboard", plan["recommended_defaults"])

    def test_swarm_mode_activates_for_booking_business(self):
        swarm = SwarmMode()
        self.assertTrue(swarm.should_activate("Build me a plumber booking business"))
        self.assertIn("security", swarm.as_markdown("Build me a plumber booking business"))

    def test_plumber_booking_scaffold_has_business_files_and_tests(self):
        scaffold = ScaffoldRegistry().match("Build me a plumber booking business", {"target_stack": "generic"})

        self.assertIsNotNone(scaffold)
        self.assertEqual(scaffold.name, "plumber_booking_business_pack")
        self.assertIn("app/book/page.tsx", scaffold.files)
        self.assertIn("app/api/checkout/route.ts", scaffold.files)
        self.assertIn("test/email.test.ts", scaffold.files)
        self.assertIn("SWARM_PLAN.md", scaffold.files)
        self.assertIn("npm test", scaffold.verification_commands)


if __name__ == "__main__":
    unittest.main()
