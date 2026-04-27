import json
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.response_schema import AgentResponse
from tools.cleanup_runtime import cleanup_directory

_benchmark_path = os.path.join(PROJECT_ROOT, "test", "benchmark", "automated_benchmarks.py")
_benchmark_spec = importlib.util.spec_from_file_location("automated_benchmarks", _benchmark_path)
_benchmark_module = importlib.util.module_from_spec(_benchmark_spec)
_benchmark_spec.loader.exec_module(_benchmark_module)
inspect_generated_project = _benchmark_module.inspect_generated_project


class TestConfigApiCleanup(unittest.TestCase):
    def test_agent_response_legacy_unpack_and_dict(self):
        response = AgentResponse(answer="clean", raw="raw", files=["main.py"], status="ok", metadata={"mode": "FAST"})
        raw, clean = response
        self.assertEqual(raw, "raw")
        self.assertEqual(clean, "clean")
        self.assertEqual(response.to_dict()["files"], ["main.py"])

    def test_cleanup_respects_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_dir = root / "old"
            new_dir = root / "new"
            old_dir.mkdir()
            new_dir.mkdir()
            old_time = time.time() - 48 * 3600
            os.utime(old_dir, (old_time, old_time))

            removed = cleanup_directory(root, retention_hours=24)

            self.assertIn(str(old_dir), removed)
            self.assertFalse(old_dir.exists())
            self.assertTrue(new_dir.exists())

    def test_benchmark_project_assertions_inspect_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "routes").mkdir(parents=True)
            (root / "test").mkdir(parents=True)
            (root / "PLAN.md").write_text("# Plan", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"scripts": {"start": "node dist/index.js", "test": "vitest run"}}), encoding="utf-8")
            (root / "src" / "index.ts").write_text("import { routes } from './routes/routes';", encoding="utf-8")
            (root / "src" / "routes" / "routes.ts").write_text("routes.get('/records', a); routes.post('/records', b);", encoding="utf-8")
            (root / "test" / "routes.test.ts").write_text("test('/api/health', a); test('/api/records', b);", encoding="utf-8")

            ok, errors = inspect_generated_project(str(root), "express")

            self.assertTrue(ok, errors)


if __name__ == "__main__":
    unittest.main()
