import argparse
import os
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import config


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def cleanup_directory(root: Path, retention_hours: int, dry_run: bool = False) -> list[str]:
    if not root.exists():
        return []
    cutoff = time.time() - retention_hours * 3600
    removed = []
    root = root.resolve()

    for child in root.iterdir():
        if not _is_within_root(child, root):
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime > cutoff:
            continue
        removed.append(str(child))
        if dry_run:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely clean old Erasmus X runtime sandboxes/logs.")
    parser.add_argument("--runtime-root", default=config.RUNTIME_ROOT)
    parser.add_argument("--retention-hours", type=int, default=config.SANDBOX_RETENTION_HOURS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root).resolve()
    targets = [
        runtime_root / "sandboxes",
        runtime_root / "logs",
    ]

    all_removed = []
    for target in targets:
        if not _is_within_root(target, runtime_root):
            raise SystemExit(f"Refusing to clean outside runtime root: {target}")
        removed = cleanup_directory(target, args.retention_hours, args.dry_run)
        all_removed.extend(removed)
        action = "Would remove" if args.dry_run else "Removed"
        print(f"{action} {len(removed)} item(s) from {target}")

    if all_removed:
        print("\n".join(all_removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
