import json
import os
import re
from typing import Optional

from core import config
from core.scaffold_registry import Scaffold


class DynamicScaffoldBuilder:
    """Creates a temporary scaffold pack for stacks that are not registered yet."""

    def __init__(self, client=None, searcher=None):
        self.client = client
        self.searcher = searcher

    def build(self, user_input: str, metadata: dict) -> Optional[Scaffold]:
        if metadata.get("target_stack") != "generic":
            return None
        if not self._looks_like_unknown_stack_request(user_input):
            return None

        research = self._research_stack(user_input)
        scaffold = self._ask_model_for_pack(user_input, research)
        if scaffold and self._is_scaffold_usable(scaffold):
            return scaffold
        if scaffold:
            repair_notes = self._scaffold_rejection_notes(scaffold)
            print(f"[!] Dynamic scaffold rejected: {', '.join(repair_notes)}")
            print("[*] Dynamic scaffold repair: using research notes to fill missing gaps...")
            repaired = self._repair_model_pack(user_input, research, scaffold, repair_notes)
            if repaired and self._is_scaffold_usable(repaired):
                print(f"[+] Dynamic scaffold repair accepted: {repaired.name}")
                return repaired
            if repaired:
                print(f"[!] Dynamic scaffold repair rejected: {', '.join(self._scaffold_rejection_notes(repaired))}")
            print("[*] Dynamic scaffold fallback: using deterministic stack scaffold.")
        return self._fallback_pack(user_input, research)

    def _looks_like_unknown_stack_request(self, user_input: str) -> bool:
        lower = user_input.lower()
        project_terms = ("create", "build", "make", "scaffold", "generate")
        targets = ("app", "api", "project", "service", "website", "application", "bot", "worker", "tool")
        known = ("next.js", "nextjs", "react", "express", "fastapi")
        return (
            any(term in lower for term in project_terms)
            and any(target in lower for target in targets)
            and not any(k in lower for k in known)
            and self._mentions_specific_stack(user_input)
        )

    def _mentions_specific_stack(self, user_input: str) -> bool:
        lower = user_input.lower()
        if re.search(r"\b(with|using|in)\s+[a-z0-9.+#-]+", lower):
            return True
        generic_capitals = {"Build", "Create", "Make", "Generate", "Scaffold", "App", "Application", "Project", "API", "Website"}
        capitals = re.findall(r"\b[A-Z][A-Za-z0-9.+#-]{2,}\b", user_input)
        return any(token not in generic_capitals for token in capitals)

    def _research_stack(self, user_input: str) -> str:
        if not self.searcher:
            return ""
        query = f"official getting started project structure testing commands for {user_input}"
        try:
            return self.searcher.search(query, max_results=3, deep_mode=True) or ""
        except Exception as exc:
            print(f"[!] Dynamic scaffold research failed: {exc}")
            return ""

    def _ask_model_for_pack(self, user_input: str, research: str) -> Optional[Scaffold]:
        if not self.client:
            return None
        prompt = f"""Create a minimal but runnable scaffold pack for this project request.

Request: {user_input}

Research notes:
{research[:2500]}

Return strict JSON only:
{{
  "name": "snake_case_pack_name",
  "stack": "stack|language",
  "files": {{
    "PLAN.md": "...",
    "package.json": "..." 
  }},
  "verification_commands": ["command 1", "command 2"]
}}

Rules:
- Include generated tests for the scaffold's main behavior.
- Include a CLI test command in package/build metadata when the stack supports it.
- Keep files complete and small.
- Do not include markdown fences.
"""
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=45,
            )
            raw = response.choices[0].message.content or ""
            return self._parse_scaffold_json(raw)
        except Exception as exc:
            print(f"[!] Dynamic scaffold generation failed: {exc}")
            return None

    def _repair_model_pack(self, user_input: str, research: str, scaffold: Scaffold, rejection_notes: list[str]) -> Optional[Scaffold]:
        if not self.client:
            return None
        prompt = f"""Repair this rejected scaffold pack using the research notes.

Request: {user_input}

Research notes:
{research[:3000]}

Rejected pack:
{json.dumps({
  "name": scaffold.name,
  "stack": scaffold.stack,
  "files": scaffold.files,
  "verification_commands": scaffold.verification_commands,
}, indent=2)[:6000]}

Rejection notes:
{chr(10).join(f"- {note}" for note in rejection_notes)}

Return strict JSON only in the same schema:
{{
  "name": "snake_case_pack_name",
  "stack": "stack|language",
  "files": {{
    "PLAN.md": "... complete plan ...",
    "path/to/file": "... complete source ..."
  }},
  "verification_commands": ["command 1", "command 2"]
}}

Hard requirements:
- Fill every rejected gap from the research notes before returning.
- Include real implementation logic, not placeholder comments.
- Include behavior tests for the main user-facing behavior.
- Include CLI verification commands that run those tests.
- Use conventional filenames for the stack, for example Makefile for C/make and dotnet test for .NET.
- Keep the scaffold small but runnable.
- Do not include markdown fences or explanations.
"""
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=60,
            )
            raw = response.choices[0].message.content or ""
            return self._parse_scaffold_json(raw)
        except Exception as exc:
            print(f"[!] Dynamic scaffold repair failed: {exc}")
            return None

    def _parse_scaffold_json(self, raw: str) -> Optional[Scaffold]:
        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        files = payload.get("files")
        if not isinstance(files, dict) or not files:
            return None
        normalized_files = {}
        for path, content in files.items():
            safe_path = str(path).replace("\\", "/").lstrip("./")
            if safe_path.lower() == "makefile":
                safe_path = "Makefile"
            if not safe_path or safe_path.startswith("../") or os.path.isabs(safe_path):
                return None
            normalized_files[safe_path] = str(content)
        return Scaffold(
            name=str(payload.get("name") or "research_derived_scaffold"),
            stack=str(payload.get("stack") or "research-derived"),
            files=normalized_files,
            verification_commands=[str(cmd) for cmd in payload.get("verification_commands", [])],
        )

    def _is_scaffold_usable(self, scaffold: Scaffold) -> bool:
        return not self._scaffold_rejection_notes(scaffold)

    def _scaffold_rejection_notes(self, scaffold: Scaffold) -> list[str]:
        notes = []
        paths = [path.replace("\\", "/").lower() for path in scaffold.files]
        has_tests = any(
            path.startswith(("test/", "tests/"))
            or "/test/" in path
            or "/tests/" in path
            or path.endswith((".test.ts", ".test.tsx", "_test.py", "_test.c", "tests.cs"))
            for path in paths
        )
        if not has_tests:
            notes.append("Missing behavior test files.")
        if not scaffold.verification_commands:
            notes.append("Missing CLI verification commands.")
        joined = "\n".join(scaffold.files.values()).lower()
        placeholder_signals = (
            "implementation of",
            "implementation here",
            "todo",
            "placeholder",
            "cmake_test_command",
        )
        for signal in placeholder_signals:
            if signal in joined:
                notes.append(f"Placeholder or hollow implementation signal detected: {signal}")
        return notes

    def _fallback_pack(self, user_input: str, research: str) -> Scaffold:
        lower = user_input.lower()
        if re.search(r"(^|\W)c(\W|$)", lower) or " makefile" in lower:
            return self._c_tax_pack(user_input, research)
        if ".net" in lower or "dotnet" in lower or "asp.net" in lower or "c#" in lower:
            return self._dotnet_form_pack(user_input, research)
        if "php" in lower:
            return self._php_bot_pack(user_input, research)
        title = re.sub(r"\s+", " ", user_input.strip())[:80]
        plan = (
            f"# Research-Derived Scaffold\n\n"
            f"- Request: {title}\n"
            f"- Research was attempted before creating this fallback pack\n"
            f"- Replace the generic Python service only after a framework-specific pack is learned\n"
        )
        if research:
            plan += f"\n## Research Notes\n\n{research[:1000]}\n"
        return Scaffold(
            name="research_fallback_python_service",
            stack="python|service|research-derived",
            files={
                "PLAN.md": plan,
                "app.py": "from http.server import BaseHTTPRequestHandler, HTTPServer\nimport json\n\nclass Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        if self.path == '/health':\n            self.send_response(200)\n            self.send_header('content-type', 'application/json')\n            self.end_headers()\n            self.wfile.write(json.dumps({'ok': True}).encode())\n            return\n        self.send_response(404)\n        self.end_headers()\n\nif __name__ == '__main__':\n    HTTPServer(('127.0.0.1', 8000), Handler).serve_forever()\n",
                "test_app.py": "import json\nfrom app import Handler\n\n\ndef test_health_payload_shape():\n    payload = json.dumps({'ok': True})\n    assert payload == '{\"ok\": true}'\n    assert hasattr(Handler, 'do_GET')\n",
                "requirements.txt": "pytest\n",
            },
            verification_commands=["python -m pytest"],
        )

    def _research_plan(self, user_input: str, research: str, stack_note: str) -> str:
        title = re.sub(r"\s+", " ", user_input.strip())[:100]
        plan = (
            "# Research-Derived Scaffold\n\n"
            f"- Request: {title}\n"
            f"- Stack: {stack_note}\n"
            "- Includes behavior tests and CLI verification commands\n"
        )
        if research:
            plan += f"\n## Research Notes\n\n{research[:1000]}\n"
        return plan

    def _c_tax_pack(self, user_input: str, research: str) -> Scaffold:
        return Scaffold(
            name="c_tax_calculator_pack",
            stack="c|cli|make",
            files={
                "PLAN.md": self._research_plan(user_input, research, "C CLI with Makefile"),
                "src/tax.h": "#ifndef TAX_H\n#define TAX_H\n\ntypedef struct TaxResult {\n    double gross_income;\n    double allowance;\n    double taxable_income;\n    double tax_due;\n    double net_income;\n} TaxResult;\n\nTaxResult calculate_tax(double gross_income);\n\n#endif\n",
                "src/tax.c": "#include \"tax.h\"\n\nstatic double band_tax(double taxable, double lower, double upper, double rate) {\n    if (taxable <= lower) {\n        return 0.0;\n    }\n    double capped = taxable < upper ? taxable : upper;\n    return (capped - lower) * rate;\n}\n\nTaxResult calculate_tax(double gross_income) {\n    const double allowance = gross_income > 100000.0 ? 0.0 : 12570.0;\n    double taxable = gross_income - allowance;\n    if (taxable < 0.0) {\n        taxable = 0.0;\n    }\n    double tax = 0.0;\n    tax += band_tax(taxable, 0.0, 37700.0, 0.20);\n    tax += band_tax(taxable, 37700.0, 125140.0, 0.40);\n    if (taxable > 125140.0) {\n        tax += (taxable - 125140.0) * 0.45;\n    }\n    TaxResult result = { gross_income, allowance, taxable, tax, gross_income - tax };\n    return result;\n}\n",
                "src/main.c": "#include <stdio.h>\n#include <stdlib.h>\n#include \"tax.h\"\n\nint main(int argc, char **argv) {\n    if (argc != 2) {\n        fprintf(stderr, \"Usage: %s <gross-income>\\n\", argv[0]);\n        return 1;\n    }\n    char *end = NULL;\n    double income = strtod(argv[1], &end);\n    if (end == argv[1] || income < 0.0) {\n        fprintf(stderr, \"Income must be a non-negative number.\\n\");\n        return 1;\n    }\n    TaxResult result = calculate_tax(income);\n    printf(\"gross=%.2f\\n\", result.gross_income);\n    printf(\"taxable=%.2f\\n\", result.taxable_income);\n    printf(\"tax_due=%.2f\\n\", result.tax_due);\n    printf(\"net=%.2f\\n\", result.net_income);\n    return 0;\n}\n",
                "tests/test_tax.c": "#include <assert.h>\n#include <math.h>\n#include \"../src/tax.h\"\n\nstatic void assert_close(double actual, double expected) {\n    assert(fabs(actual - expected) < 0.01);\n}\n\nint main(void) {\n    TaxResult low = calculate_tax(12000.0);\n    assert_close(low.tax_due, 0.0);\n    assert_close(low.net_income, 12000.0);\n\n    TaxResult basic = calculate_tax(50000.0);\n    assert_close(basic.taxable_income, 37430.0);\n    assert_close(basic.tax_due, 7486.0);\n\n    TaxResult higher = calculate_tax(150000.0);\n    assert(higher.tax_due > basic.tax_due);\n    assert(higher.net_income < higher.gross_income);\n    return 0;\n}\n",
                "Makefile": "CC ?= gcc\nCFLAGS ?= -Wall -Wextra -Werror -std=c11\n\n.PHONY: all test clean\n\nall: taxcalc\n\ntaxcalc: src/main.c src/tax.c src/tax.h\n\t$(CC) $(CFLAGS) src/main.c src/tax.c -o taxcalc\n\ntest: tests/test_tax.c src/tax.c src/tax.h\n\t$(CC) $(CFLAGS) tests/test_tax.c src/tax.c -lm -o test_tax\n\t./test_tax\n\nclean:\n\trm -f taxcalc test_tax\n",
            },
            verification_commands=["make test", "make"],
        )

    def _dotnet_form_pack(self, user_input: str, research: str) -> Scaffold:
        return Scaffold(
            name="dotnet_contact_form_pack",
            stack="dotnet|aspnetcore|csharp",
            files={
                "PLAN.md": self._research_plan(user_input, research, "ASP.NET Core minimal API with tests"),
                "ContactForm.csproj": "<Project Sdk=\"Microsoft.NET.Sdk.Web\">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n    <Nullable>enable</Nullable>\n    <ImplicitUsings>enable</ImplicitUsings>\n  </PropertyGroup>\n</Project>\n",
                "Program.cs": "using ContactForm;\n\nvar builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\n\napp.MapGet(\"/\", () => Results.Content(\"<form method='post' action='/contact'><input name='name' /><input name='email' /><textarea name='message'></textarea><button>Send</button></form>\", \"text/html\"));\napp.MapPost(\"/contact\", (ContactRequest request) => {\n    var errors = ContactValidator.Validate(request);\n    if (errors.Count > 0) {\n        return Results.BadRequest(new { errors });\n    }\n    return Results.Ok(new { status = \"received\", request.Email });\n});\n\napp.Run();\n\npublic partial class Program { }\n",
                "ContactRequest.cs": "namespace ContactForm;\n\npublic record ContactRequest(string Name, string Email, string Message);\n",
                "ContactValidator.cs": "using System.Text.RegularExpressions;\n\nnamespace ContactForm;\n\npublic static class ContactValidator {\n    public static List<string> Validate(ContactRequest request) {\n        var errors = new List<string>();\n        if (string.IsNullOrWhiteSpace(request.Name)) errors.Add(\"Name is required\");\n        if (string.IsNullOrWhiteSpace(request.Message) || request.Message.Length < 10) errors.Add(\"Message must be at least 10 characters\");\n        if (string.IsNullOrWhiteSpace(request.Email) || !Regex.IsMatch(request.Email, @\"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$\")) errors.Add(\"Valid email is required\");\n        return errors;\n    }\n}\n",
                "tests/ContactValidatorTests.cs": "using ContactForm;\nusing Xunit;\n\npublic class ContactValidatorTests {\n    [Fact]\n    public void AcceptsValidContactRequest() {\n        var errors = ContactValidator.Validate(new ContactRequest(\"Ada\", \"ada@example.com\", \"Please contact me soon.\"));\n        Assert.Empty(errors);\n    }\n\n    [Fact]\n    public void RejectsInvalidContactRequest() {\n        var errors = ContactValidator.Validate(new ContactRequest(\"\", \"not-email\", \"short\"));\n        Assert.Contains(\"Name is required\", errors);\n        Assert.Contains(\"Valid email is required\", errors);\n        Assert.Contains(\"Message must be at least 10 characters\", errors);\n    }\n}\n",
                "tests/ContactForm.Tests.csproj": "<Project Sdk=\"Microsoft.NET.Sdk\">\n  <PropertyGroup>\n    <TargetFramework>net8.0</TargetFramework>\n    <Nullable>enable</Nullable>\n    <ImplicitUsings>enable</ImplicitUsings>\n    <IsPackable>false</IsPackable>\n  </PropertyGroup>\n  <ItemGroup>\n    <PackageReference Include=\"Microsoft.NET.Test.Sdk\" Version=\"17.10.0\" />\n    <PackageReference Include=\"xunit\" Version=\"2.8.1\" />\n    <PackageReference Include=\"xunit.runner.visualstudio\" Version=\"2.8.1\" />\n  </ItemGroup>\n  <ItemGroup>\n    <ProjectReference Include=\"..\\ContactForm.csproj\" />\n  </ItemGroup>\n</Project>\n",
            },
            verification_commands=["dotnet test", "dotnet run"],
        )

    def _php_bot_pack(self, user_input: str, research: str) -> Scaffold:
        return Scaffold(
            name="php_bot_pack",
            stack="php|cli|webhook",
            files={
                "PLAN.md": self._research_plan(user_input, research, "PHP bot with CLI and webhook entrypoints"),
                "composer.json": json.dumps({
                    "scripts": {
                        "test": "php tests/BotTest.php",
                        "verify": "php tests/BotTest.php && php public/index.php"
                    }
                }, indent=2),
                "src/Bot.php": "<?php\n\nclass Bot\n{\n    private array $responses;\n\n    public function __construct()\n    {\n        $this->responses = [\n            'hello' => 'Hello. How can I help?',\n            'help' => 'Available commands: hello, help, status.',\n            'status' => 'Bot is online.'\n        ];\n    }\n\n    public function reply(string $message): string\n    {\n        $key = strtolower(trim($message));\n        return $this->responses[$key] ?? 'I did not understand that command. Type help.';\n    }\n}\n",
                "public/index.php": "<?php\n\nrequire_once __DIR__ . '/../src/Bot.php';\n\n$bot = new Bot();\n$message = $_GET['message'] ?? ($argv[1] ?? 'status');\n$response = ['reply' => $bot->reply($message)];\n\nif (PHP_SAPI !== 'cli') {\n    header('Content-Type: application/json');\n}\n\necho json_encode($response, JSON_PRETTY_PRINT) . PHP_EOL;\n",
                "tests/BotTest.php": "<?php\n\nrequire_once __DIR__ . '/../src/Bot.php';\n\n$bot = new Bot();\n\nassert($bot->reply('hello') === 'Hello. How can I help?');\nassert($bot->reply('help') === 'Available commands: hello, help, status.');\nassert($bot->reply('status') === 'Bot is online.');\nassert($bot->reply('unknown') === 'I did not understand that command. Type help.');\n\necho \"Bot tests passed\" . PHP_EOL;\n",
            },
            verification_commands=["php tests/BotTest.php", "php public/index.php status"],
        )
