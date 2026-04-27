import os
import tempfile
import time
import unittest

from core.request_cache import RequestCache
from core.transaction_manager import ProjectTransaction
from core.task_queue import TaskQueue
from core.model_router import ModelRouter
from core.graph_reasoner import GraphReasoner
from core.active_kg_builder import ActiveKGBuilder


class DummyKG:
    def __init__(self):
        self.triplets = []

    def add_triplet(self, subject, relation, obj):
        self.triplets.append((subject, relation, obj))

    def get_related_facts(self, entity):
        return ["app/page.tsx imports components/TodoList.tsx"]


class TestNextLevelRoadmap(unittest.TestCase):
    def test_request_cache_round_trip_and_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = RequestCache(max_bytes=1024, storage_path=os.path.join(tmp, "cache.json"))
            key = cache.fingerprint("hello", model="m")
            cache.set(key, {"raw": "hi", "clean": "hi"}, ttl=1)
            self.assertEqual(cache.get(key)["clean"], "hi")
            time.sleep(1.1)
            self.assertIsNone(cache.get(key))

    def test_transaction_rolls_back_uncommitted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tx = ProjectTransaction(tmp).begin()
            ok, _ = tx.add_file("app/page.tsx", "export default function Page() {}")
            self.assertTrue(ok)
            tx.rollback()
            self.assertFalse(os.path.exists(os.path.join(tmp, "app", "page.tsx")))

    def test_transaction_commits_staged_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tx = ProjectTransaction(tmp).begin()
            tx.add_file("app/page.tsx", "export default function Page() {}")
            committed = tx.commit()
            self.assertEqual(committed, ["app/page.tsx"])
            self.assertTrue(os.path.exists(os.path.join(tmp, "app", "page.tsx")))

    def test_task_queue_processes_jobs(self):
        queue = TaskQueue(handler=lambda payload: payload + 1, num_workers=1)
        job_id = queue.enqueue(1)
        queue.process_next()
        status = queue.get_status(job_id)
        for _ in range(20):
            if status["state"] == "completed":
                break
            time.sleep(0.05)
            status = queue.get_status(job_id)
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["result"], 2)

    def test_model_router_detects_framework(self):
        router = ModelRouter("generic", {"nextjs": "next-lora"})
        self.assertEqual(router.detect_framework("Create a Next.js app router project"), "nextjs")
        self.assertEqual(router.route("Create a Next.js app router project"), "next-lora")
        self.assertEqual(router.route("Write a shell script"), "generic")

    def test_graph_reasoner_and_active_builder(self):
        kg = DummyKG()
        reasoner = GraphReasoner(kg)
        self.assertTrue(reasoner.plan_project("todo app"))
        builder = ActiveKGBuilder(kg)
        builder.extract_from_project({"main.py": "import os\n\ndef run():\n    return os.getcwd()\n"})
        self.assertIn(("main.py", "imports", "os"), kg.triplets)
        self.assertIn(("main.py", "defines", "run"), kg.triplets)


if __name__ == "__main__":
    unittest.main()
