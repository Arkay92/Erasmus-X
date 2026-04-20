"""
brain_sync.py — DB → HypervectorDB Bridge

Ingests structured records from SQLite tables or JSON files into the
agent's hypervector brain and knowledge graph, enabling semantic search
over task/project data without SQL queries.

Usage:
    from utils.brain_sync import sync_from_sqlite, sync_from_json, sync_record

    # Generic sync from any SQLite DB
    synced = sync_from_sqlite(brain, kg, "scratch/myproject/tasks.db")

    # Sync a single dict record
    sync_record(brain, kg, {"task": "Buy milk", "status": "pending", "priority": "high"})
"""

import os
import sqlite3
import json


def record_to_text(record: dict) -> str:
    """
    Converts a dict record into a human-readable sentence for encoding.
    e.g. {"task": "Buy milk", "status": "pending"} 
      -> "Task: Buy milk | Status: pending"
    """
    parts = []
    for key, value in record.items():
        if value is None or str(value).strip() == "":
            continue
        label = str(key).replace("_", " ").title()
        parts.append(f"{label}: {value}")
    return " | ".join(parts)


def record_to_triplets(record: dict) -> list:
    """
    Extracts (subject, relation, object) KG triplets from a record.
    Uses the first non-id field as subject, remaining as object facts.
    e.g. {"task": "Buy milk", "status": "pending", "priority": "high"}
      -> [("buy milk", "has status", "pending"), ("buy milk", "has priority", "high")]
    """
    triplets = []
    keys = [k for k in record.keys() if k.lower() not in ("id", "rowid")]
    if not keys:
        return triplets

    # First meaningful field is the subject
    subject_key = keys[0]
    subject = str(record.get(subject_key, "")).strip().lower()
    if not subject:
        return triplets

    # Remaining fields become (subject, has_<field>, value) triplets
    for key in keys[1:]:
        value = record.get(key)
        if value is None or str(value).strip() == "":
            continue
        relation = f"has {key.replace('_', ' ').lower()}"
        triplets.append((subject, relation, str(value).strip().lower()))

    return triplets


def sync_record(brain, kg, record: dict, source_label: str = "") -> str:
    """
    Ingest a single dict record into the brain and knowledge graph.
    Returns the text representation that was encoded.
    """
    text = record_to_text(record)
    if source_label:
        text = f"[{source_label}] {text}"

    brain.add_document(text)

    # Add KG triplets
    for subject, relation, obj in record_to_triplets(record):
        kg.add_triplet(subject, relation, obj)

    return text


def sync_from_json(brain, kg, json_path: str) -> int:
    """
    Reads a JSON file (array of dicts) and syncs all records to the brain.
    Returns the number of records synced.
    """
    if not os.path.exists(json_path):
        print(f"[BrainSync] File not found: {json_path}")
        return 0

    label = os.path.splitext(os.path.basename(json_path))[0]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[BrainSync] Failed to load {json_path}: {e}")
        return 0

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        print(f"[BrainSync] Unsupported JSON structure in {json_path}")
        return 0

    count = 0
    for record in data:
        if isinstance(record, dict):
            sync_record(brain, kg, record, source_label=label)
            count += 1

    brain.save()
    print(f"[BrainSync] Synced {count} records from {os.path.basename(json_path)}")
    return count


def sync_from_sqlite(brain, kg, db_path: str, tables: list = None) -> int:
    """
    Reads all rows from SQLite tables and syncs them to the brain.
    If tables=None, discovers and syncs all non-system tables.
    Returns the total number of records synced.
    """
    if not os.path.exists(db_path):
        print(f"[BrainSync] DB not found: {db_path}")
        return 0

    total = 0
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()

        # Discover tables if not specified
        if not tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                label = f"{os.path.splitext(os.path.basename(db_path))[0]}.{table}"

                for row in rows:
                    record = dict(row)
                    sync_record(brain, kg, record, source_label=label)
                    total += 1

                print(f"[BrainSync] Synced {len(rows)} rows from {table}")
            except Exception as e:
                print(f"[BrainSync] Error reading table '{table}': {e}")

        conn.close()
        brain.save()

    except Exception as e:
        print(f"[BrainSync] SQLite error for {db_path}: {e}")

    print(f"[BrainSync] Total: {total} records synced from {os.path.basename(db_path)}")
    return total


def sync_project_dir(brain, kg, project_dir: str) -> int:
    """
    Scans a project directory and auto-syncs any .db and .json data files found.
    Skips config files (package.json, etc.) and plan files (PLAN.md not applicable here).
    Returns total records synced.
    """
    SKIP_FILES = {"package.json", "package-lock.json", "tsconfig.json", "PLAN.md"}
    total = 0

    if not os.path.isdir(project_dir):
        return 0

    for fname in os.listdir(project_dir):
        fpath = os.path.join(project_dir, fname)
        if fname in SKIP_FILES:
            continue

        if fname.endswith(".db"):
            total += sync_from_sqlite(brain, kg, fpath)
        elif fname.endswith(".json"):
            total += sync_from_json(brain, kg, fpath)

    return total
