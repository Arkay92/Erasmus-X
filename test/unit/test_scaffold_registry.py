import json
import unittest

from core.dynamic_scaffold_builder import DynamicScaffoldBuilder
from core.scaffold_registry import ScaffoldRegistry


class TestScaffoldRegistry(unittest.TestCase):
    def test_express_scaffold_includes_route_tests_and_cli_script(self):
        scaffold = ScaffoldRegistry().match(
            "Create an Express.js REST API for posts",
            {"target_stack": "express|typescript"},
        )

        self.assertIsNotNone(scaffold)
        self.assertIn("test/routes.test.ts", scaffold.files)
        self.assertIn("/api/health", scaffold.files["test/routes.test.ts"])
        self.assertIn("/api/records", scaffold.files["test/routes.test.ts"])

        package_data = json.loads(scaffold.files["package.json"])
        self.assertIn("test", package_data["scripts"])
        self.assertIn("npm test", scaffold.verification_commands)

    def test_booking_scaffold_includes_helper_tests(self):
        scaffold = ScaffoldRegistry().match(
            "Build a booking system with login register auth and admin dashboard",
            {"target_stack": "generic"},
        )

        self.assertIsNotNone(scaffold)
        self.assertIn("test/validation.test.ts", scaffold.files)
        self.assertIn("test/auth.test.ts", scaffold.files)
        self.assertIn("CreateBookingForm", scaffold.files["app/admin/bookings/page.tsx"])


class FakeSearcher:
    def search(self, query, max_results=3, deep_mode=False):
        return "Use official CLI, create an app file, and run tests with the stack test runner."


class FakeClient:
    class chat:
        class completions:
            @staticmethod
            def create(**_kwargs):
                class Message:
                    content = json.dumps({
                        "name": "phoenix_liveview_pack",
                        "stack": "phoenix|elixir",
                        "files": {
                            "PLAN.md": "# Phoenix App",
                            "mix.exs": "defmodule Demo.MixProject do\n  use Mix.Project\n  def project, do: [app: :demo, version: \"0.1.0\"]\nend\n",
                            "test/demo_test.exs": "ExUnit.start()\ndefmodule DemoTest do\n  use ExUnit.Case\n  test \"truth\", do: assert true\nend\n",
                        },
                        "verification_commands": ["mix test"],
                    })

                class Choice:
                    message = Message()

                class Response:
                    choices = [Choice()]

                return Response()


class WeakCClient:
    class chat:
        class completions:
            @staticmethod
            def create(**_kwargs):
                class Message:
                    content = json.dumps({
                        "name": "weak_c_pack",
                        "stack": "c",
                        "files": {
                            "main.c": "int main(void) { /* Implementation of tax calculation logic */ return 0; }",
                            "makefile": "gcc main.c -o tax_app",
                        },
                        "verification_commands": ["make"],
                    })

                class Choice:
                    message = Message()

                class Response:
                    choices = [Choice()]

                return Response()


class RepairingCClient:
    call_count = 0

    class chat:
        class completions:
            @staticmethod
            def create(**_kwargs):
                RepairingCClient.call_count += 1
                if RepairingCClient.call_count == 1:
                    payload = {
                        "name": "weak_c_pack",
                        "stack": "c",
                        "files": {
                            "main.c": "int main(void) { /* Implementation of tax calculation logic */ return 0; }",
                            "makefile": "gcc main.c -o tax_app",
                        },
                        "verification_commands": ["make"],
                    }
                else:
                    payload = {
                        "name": "repaired_c_tax_pack",
                        "stack": "c|cli|make",
                        "files": {
                            "PLAN.md": "# C Tax Calculator",
                            "src/tax.c": "double calculate_tax(double income) { return income > 10000 ? (income - 10000) * 0.2 : 0.0; }",
                            "src/main.c": "#include <stdio.h>\nextern double calculate_tax(double income);\nint main(void) { printf(\"%.2f\\n\", calculate_tax(50000)); return 0; }",
                            "tests/test_tax.c": "#include <assert.h>\nextern double calculate_tax(double income);\nint main(void) { assert(calculate_tax(50000) == 8000); return 0; }",
                            "Makefile": "test:\n\tgcc tests/test_tax.c src/tax.c -o test_tax\n\t./test_tax\n",
                        },
                        "verification_commands": ["make test"],
                    }

                class Message:
                    content = json.dumps(payload)

                class Choice:
                    message = Message()

                class Response:
                    choices = [Choice()]

                return Response()


class TestDynamicScaffoldBuilder(unittest.TestCase):
    def test_unknown_stack_uses_research_and_returns_pack_with_tests(self):
        builder = DynamicScaffoldBuilder(client=FakeClient(), searcher=FakeSearcher())
        scaffold = builder.build(
            "Build a Phoenix LiveView booking app",
            {"target_stack": "generic"},
        )

        self.assertIsNotNone(scaffold)
        self.assertEqual(scaffold.stack, "phoenix|elixir")
        self.assertIn("test/demo_test.exs", scaffold.files)
        self.assertEqual(scaffold.verification_commands, ["mix test"])

    def test_weak_model_c_pack_falls_back_to_real_c_scaffold(self):
        builder = DynamicScaffoldBuilder(client=WeakCClient(), searcher=FakeSearcher())
        scaffold = builder.build(
            "Build a C app to calculate income taxes with a CLI, tests, and a Makefile",
            {"target_stack": "generic"},
        )

        self.assertEqual(scaffold.name, "c_tax_calculator_pack")
        self.assertIn("src/tax.c", scaffold.files)
        self.assertIn("tests/test_tax.c", scaffold.files)
        self.assertIn("Makefile", scaffold.files)
        self.assertIn("make test", scaffold.verification_commands)

    def test_dotnet_prompt_gets_dotnet_fallback_when_model_unavailable(self):
        builder = DynamicScaffoldBuilder(client=None, searcher=FakeSearcher())
        scaffold = builder.build(
            "Build a .NET app to host a contact form with validation, tests, and a runnable web server",
            {"target_stack": "generic"},
        )

        self.assertEqual(scaffold.name, "dotnet_contact_form_pack")
        self.assertIn("Program.cs", scaffold.files)
        self.assertIn("tests/ContactValidatorTests.cs", scaffold.files)
        self.assertIn("dotnet test", scaffold.verification_commands)

    def test_php_prompt_gets_bot_scaffold_when_model_unavailable(self):
        builder = DynamicScaffoldBuilder(client=None, searcher=FakeSearcher())
        scaffold = builder.build(
            "Build me a bot in PHP with tests and a webhook endpoint",
            {"target_stack": "generic"},
        )

        self.assertEqual(scaffold.name, "php_bot_pack")
        self.assertIn("src/Bot.php", scaffold.files)
        self.assertIn("public/index.php", scaffold.files)
        self.assertIn("tests/BotTest.php", scaffold.files)
        self.assertIn("php tests/BotTest.php", scaffold.verification_commands)

    def test_rejected_model_pack_is_repaired_from_research_before_fallback(self):
        RepairingCClient.call_count = 0
        builder = DynamicScaffoldBuilder(client=RepairingCClient(), searcher=FakeSearcher())
        scaffold = builder.build(
            "Build a C app to calculate income taxes with a CLI, tests, and a Makefile",
            {"target_stack": "generic"},
        )

        self.assertEqual(scaffold.name, "repaired_c_tax_pack")
        self.assertEqual(RepairingCClient.call_count, 2)
        self.assertIn("tests/test_tax.c", scaffold.files)
        self.assertEqual(scaffold.verification_commands, ["make test"])


if __name__ == "__main__":
    unittest.main()
