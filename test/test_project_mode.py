"""
test_project_mode.py -- Comprehensive test suite for:
  1. BrainSync unit encoding (record_to_text, record_to_triplets)
  2. sync_record -> brain + KG
  3. sync_from_json
  4. sync_from_sqlite
  5. sync_project_dir (mixed .db + .json)
  6. Agent manual sync trigger via chat

Run from project root:
    python test/test_project_mode.py
"""

import os
import sys
import json
import sqlite3
import shutil

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vector_store import HypervectorDB
from core.knowledge_graph import KnowledgeGraph
from utils.web_search import WebSearcher
from utils.brain_sync import (
    record_to_text, record_to_triplets,
    sync_record, sync_from_json, sync_from_sqlite, sync_project_dir
)

_results = []

def check(label, condition, detail=""):
    status = "[PASS]" if condition else "[FAIL]"
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n         -> {detail}"
    print(msg)
    _results.append((label, condition))
    return condition

def make_brain(name="test"):
    brain = HypervectorDB(filename=f"memories/test_{name}.pt", dim=2000)
    kg = KnowledgeGraph(storage=brain)
    return brain, kg

def make_sqlite_db(path, rows):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, priority TEXT)")
    conn.executemany("INSERT INTO tasks (title, status, priority) VALUES (?, ?, ?)",
                     [(r["title"], r["status"], r["priority"]) for r in rows])
    conn.commit()
    conn.close()


# ── Suite 1: record_to_text / record_to_triplets ──────────────────────────────

def test_unit_encoding():
    print("\n-- Suite 1: Unit -- record_to_text / record_to_triplets --")

    r = {"task": "Write tests", "status": "pending", "priority": "high"}
    text = record_to_text(r)
    check("record_to_text includes all field values",
          "Task: Write tests" in text and "Status: pending" in text, text)

    triplets = record_to_triplets(r)
    subjects = [t[0] for t in triplets]
    relations = [t[1] for t in triplets]
    check("record_to_triplets subject == first field value",
          all(s == "write tests" for s in subjects), str(subjects))
    check("record_to_triplets relation names are correct",
          "has status" in relations and "has priority" in relations, str(relations))

    check("record_to_text handles empty dict", record_to_text({}) == "")

    sparse = {"name": "Alpha", "description": None, "value": ""}
    sparse_text = record_to_text(sparse)
    check("record_to_text omits None/empty values",
          "None" not in sparse_text and "Description" not in sparse_text, sparse_text)


# ── Suite 2: sync_record ──────────────────────────────────────────────────────

def test_sync_record():
    print("\n-- Suite 2: sync_record -> brain + KG --")
    brain, kg = make_brain("sync_record")

    record = {"task": "Deploy feature", "status": "done", "priority": "critical"}
    text = sync_record(brain, kg, record, source_label="sprint")

    check("sync_record returns non-empty text", bool(text), text)
    check("source_label in encoded text", "[sprint]" in text, text)
    check("document added to brain", len(brain.documents) > 0, f"{len(brain.documents)} docs")

    results = brain.search("deploy", threshold=0.05, top_k=3)
    check("brain.search finds record after sync_record",
          any("Deploy feature" in r[1] for r in results),
          str([r[1][:60] for r in results]))

    facts = kg.get_related_facts("deploy feature")
    check("KG stores status triplet", any("done" in f for f in facts), str(facts))
    check("KG stores priority triplet", any("critical" in f for f in facts), str(facts))


# ── Suite 3: sync_from_json ───────────────────────────────────────────────────

def test_sync_from_json():
    print("\n-- Suite 3: sync_from_json --")
    brain, kg = make_brain("json")

    test_file = "scratch/test_tasks_suite.json"
    os.makedirs("scratch", exist_ok=True)
    tasks = [
        {"id": 1, "task": "Fix login bug",       "status": "done",        "priority": "high"},
        {"id": 2, "task": "Add search filter",    "status": "pending",     "priority": "medium"},
        {"id": 3, "task": "Write documentation",  "status": "in_progress", "priority": "low"},
        {"id": 4, "task": "Optimise query speed", "status": "pending",     "priority": "high"},
    ]
    with open(test_file, "w") as f:
        json.dump(tasks, f)

    count = sync_from_json(brain, kg, test_file)
    check("sync_from_json returns correct count", count == 4, f"got {count}")
    check("all records in brain documents", len(brain.documents) >= 4, f"{len(brain.documents)}")

    res_high = brain.search("high priority", threshold=0.05, top_k=5)
    check("semantic search surfaces high priority tasks",
          sum(1 for r in res_high if "high" in r[1].lower()) >= 1,
          str([r[1][:50] for r in res_high]))

    facts = kg.get_related_facts("fix login bug")
    check("KG stores 'done' status for login bug", any("done" in f for f in facts), str(facts))

    check("handles missing file gracefully",
          sync_from_json(brain, kg, "scratch/nonexistent.json") == 0)

    os.remove(test_file)


# ── Suite 4: sync_from_sqlite ─────────────────────────────────────────────────

def test_sync_from_sqlite():
    print("\n-- Suite 4: sync_from_sqlite --")
    brain, kg = make_brain("sqlite")

    db_path = "scratch/test_suite.db"
    rows = [
        {"title": "Migrate database schema", "status": "done",        "priority": "high"},
        {"title": "Set up CI pipeline",       "status": "pending",     "priority": "high"},
        {"title": "Code review backlog",       "status": "in_progress","priority": "medium"},
    ]
    make_sqlite_db(db_path, rows)

    count = sync_from_sqlite(brain, kg, db_path)
    check("sync_from_sqlite correct count", count == 3, f"got {count}")

    res = brain.search("database migration", threshold=0.05, top_k=3)
    check("semantic search finds DB migration task",
          any("Migrate database schema" in r[1] for r in res),
          str([r[1][:60] for r in res]))

    facts = kg.get_related_facts("migrate database schema")
    check("KG stores status from SQLite row", any("done" in f for f in facts), str(facts))

    check("handles missing DB gracefully",
          sync_from_sqlite(brain, kg, "scratch/no.db") == 0)

    os.remove(db_path)


# ── Suite 5: sync_project_dir ─────────────────────────────────────────────────

def test_sync_project_dir():
    print("\n-- Suite 5: sync_project_dir (mixed .db + .json) --")
    brain, kg = make_brain("projdir")

    proj = "scratch/test_proj_suite"
    os.makedirs(proj, exist_ok=True)

    planets = [
        {"name": "Aethon", "type": "Gas Giant",  "moons": 14},
        {"name": "Verath", "type": "Terrestrial", "moons": 2},
    ]
    with open(os.path.join(proj, "planets.json"), "w") as f:
        json.dump(planets, f)

    rows = [{"title": "Map star systems", "status": "pending", "priority": "high"}]
    make_sqlite_db(os.path.join(proj, "missions.db"), rows)

    with open(os.path.join(proj, "main.py"), "w") as f:
        f.write("print('hello')")
    with open(os.path.join(proj, "package.json"), "w") as f:
        json.dump({"name": "app", "version": "1.0"}, f)

    total = sync_project_dir(brain, kg, proj)
    check("syncs .json + .db records (excludes package.json + .py)", total == 3, f"got {total}")
    check("package.json not in brain documents",
          not any("package.json" in d for d in brain.documents))

    res = brain.search("gas giant planet", threshold=0.05, top_k=3)
    check("planetary JSON record is semantically searchable",
          any("Gas Giant" in r[1] or "Aethon" in r[1] for r in res),
          str([r[1][:60] for r in res]))

    shutil.rmtree(proj)


# ── Suite 6: Agent manual sync trigger ───────────────────────────────────────

def test_agent_manual_sync():
    print("\n-- Suite 6: Agent 'sync json <path>' trigger --")
    print("   (Requires LLM server to be running)")
    from core.agent import NeurosymbolicAgent

    brain, kg = make_brain("agent_sync")
    agent = NeurosymbolicAgent(brain, kg, WebSearcher())

    test_file = "scratch/agent_sync_test.json"
    os.makedirs("scratch", exist_ok=True)
    data = [
        {"task": "Refactor memory module", "status": "pending", "priority": "high"},
        {"task": "Benchmark suite update",  "status": "done",   "priority": "medium"},
    ]
    with open(test_file, "w") as f:
        json.dump(data, f)

    try:
        raw, clean = agent.chat(f"sync json {test_file}")
    except Exception as e:
        print(f"   [SKIP] LLM server not available: {e}")
        _results.append(("agent returns BrainSync confirmation", None))
        _results.append(("synced records in agent brain", None))
        _results.append(("manually synced record is semantically retrievable", None))
        if os.path.exists(test_file):
            os.remove(test_file)
        return

    # Check for connection error in response
    if raw and "Connection error" in raw:
        print("   [SKIP] LLM server not reachable -- skipping agent integration checks.")
        _results.append(("agent returns BrainSync confirmation", None))
        _results.append(("synced records in agent brain", None))
        _results.append(("manually synced record is semantically retrievable", None))
    else:
        check("agent returns BrainSync confirmation", "BrainSync" in (raw or ""), str(raw)[:80])
        check("synced records in agent brain", len(brain.documents) >= 2, f"{len(brain.documents)} docs")
        res = brain.search("refactor memory", threshold=0.05, top_k=3)
        check("manually synced record is semantically retrievable",
              any("Refactor memory module" in r[1] for r in res),
              str([r[1][:60] for r in res]))

    if os.path.exists(test_file):
        os.remove(test_file)



# ── Suite 7: Full project-mode end-to-end test ───────────────────────────────

def test_full_project_mode():
    """
    End-to-end test that fires a real project request through the agent and checks:
      1. A new project_ directory is created in scratch/
      2. PLAN.md is written inside it
      3. 2+ Python source files were generated
      4. main.py has valid syntax (no import/syntax errors)
      5. Agent brain has project-related documents after build
      6. Project content is semantically searchable in brain
    """
    print("\n-- Suite 7: Full Project Mode End-to-End --")
    print("   (Requires LLM server to be running)")

    import subprocess
    from core.agent import NeurosymbolicAgent

    SKIP_LABELS = [
        "project directory created in scratch/",
        "PLAN.md written inside project dir",
        "2+ Python source files created",
        "main.py has valid Python syntax",
        "brain has project documents after build",
        "project content semantically searchable in brain",
    ]

    brain, kg = make_brain("project_e2e")
    agent = NeurosymbolicAgent(brain, kg, WebSearcher())

    scratch_root = os.path.abspath("scratch")
    os.makedirs(scratch_root, exist_ok=True)
    before_dirs = set(d for d in os.listdir(scratch_root) if d.startswith("project_"))

    prompt = (
        "Create a Project: 'Task Tracker'. "
        "Build a multi-file Python app with: "
        "main.py (CLI entry point that adds and lists tasks), "
        "db.py (SQLite persistence with add_task and get_tasks), "
        "and a PLAN.md describing the architecture."
    )
    print(f"   Sending: {prompt[:90]}...")

    try:
        raw, clean = agent.chat(prompt)
    except Exception as e:
        print(f"   [SKIP] LLM server not available: {e}")
        for label in SKIP_LABELS:
            _results.append((label, None))
        return

    if raw and "Connection error" in raw:
        print("   [SKIP] LLM server not reachable.")
        for label in SKIP_LABELS:
            _results.append((label, None))
        return

    # ── 1. Project directory created ─────────────────────────────────────────
    after_dirs = set(d for d in os.listdir(scratch_root) if d.startswith("project_"))
    new_dirs = sorted(after_dirs - before_dirs)
    proj_created = len(new_dirs) > 0
    check("project directory created in scratch/", proj_created,
          f"new dirs: {new_dirs}" if new_dirs else "no new project_ dir found")

    if not proj_created:
        for label in SKIP_LABELS[1:]:
            _results.append((label, False))
        return

    proj_dir = os.path.join(scratch_root, new_dirs[-1])
    files_in_proj = os.listdir(proj_dir)
    print(f"   Dir : {new_dirs[-1]}")
    print(f"   Files: {files_in_proj}")

    # ── 2. PLAN.md exists ────────────────────────────────────────────────────
    check("PLAN.md written inside project dir", "PLAN.md" in files_in_proj,
          str(files_in_proj))

    # ── 3. 2+ Python source files ────────────────────────────────────────────
    py_files = [f for f in files_in_proj if f.endswith(".py")]
    check("2+ Python source files created", len(py_files) >= 2,
          f"found: {py_files}")

    # ── 4. main.py has valid Python syntax ───────────────────────────────────
    main_path = os.path.join(proj_dir, "main.py")
    if os.path.exists(main_path):
        try:
            result = subprocess.run(
                ["python", "-c",
                 f"import ast; ast.parse(open(r'{main_path}').read()); print('OK')"],
                capture_output=True, text=True, timeout=10
            )
            syntax_ok = result.returncode == 0 and "OK" in result.stdout
            check("main.py has valid Python syntax", syntax_ok,
                  result.stderr[:120] if not syntax_ok else "syntax OK")
        except Exception as e:
            check("main.py has valid Python syntax", False, str(e))
    else:
        check("main.py has valid Python syntax", False, "main.py not found in project dir")

    # ── 5. Brain has project documents ───────────────────────────────────────
    check("brain has project documents after build",
          len(brain.documents) > 0,
          f"{len(brain.documents)} docs")

    # ── 6. Project content semantically searchable ────────────────────────────
    res = brain.search("task tracker sqlite", threshold=0.05, top_k=3)
    check("project content semantically searchable in brain",
          len(res) > 0,
          str([r[1][:60] for r in res]))




def run_all():
    print("\n" + "="*60)
    print("  NEUROSYMBOLIC AGENT -- PROJECT & BRAIN SYNC TEST SUITE")
    print("="*60)

    test_unit_encoding()
    test_sync_record()
    test_sync_from_json()
    test_sync_from_sqlite()
    test_sync_project_dir()
    test_agent_manual_sync()
    test_full_project_mode()

    passed  = sum(1 for _, ok in _results if ok is True)
    failed  = sum(1 for _, ok in _results if ok is False)
    skipped = sum(1 for _, ok in _results if ok is None)
    total   = len(_results)

    print("\n" + "="*60)
    print(f"  RESULTS: {passed} passed  |  {failed} failed  |  {skipped} skipped  ({total} total)")
    print("="*60)

    if failed:
        print("\nFailed checks:")
        for name, ok in _results:
            if ok is False:
                print(f"  [FAIL]  {name}")
    if skipped:
        print("\nSkipped checks (server required):")
        for name, ok in _results:
            if ok is None:
                print(f"  [SKIP]  {name}")



if __name__ == "__main__":
    run_all()
