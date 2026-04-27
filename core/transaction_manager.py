import os
import shutil
import tempfile
from typing import Callable, Optional


class ProjectTransaction:
    """Stages project writes and commits them atomically per extraction batch."""

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self.staging_dir: Optional[str] = None
        self.generated_files: list[str] = []
        self._active = False

    def begin(self) -> "ProjectTransaction":
        os.makedirs(self.project_root, exist_ok=True)
        self.staging_dir = tempfile.mkdtemp(prefix=".staging_", dir=self.project_root)
        self.generated_files = []
        self._active = True
        return self

    def add_file(self, relative_path: str, content: str, verifier: Optional[Callable[[str, str], tuple[bool, str]]] = None) -> tuple[bool, str]:
        if not self._active or not self.staging_dir:
            raise RuntimeError("transaction has not been started")
        safe_rel = relative_path.replace("\\", "/").lstrip("/")
        final_path = os.path.abspath(os.path.join(self.project_root, safe_rel))
        if not final_path.startswith(self.project_root + os.sep) and final_path != self.project_root:
            return False, "Path escapes project root"
        if verifier:
            ok, err = verifier(safe_rel, content)
            if not ok:
                return False, err
        staged_path = os.path.join(self.staging_dir, safe_rel)
        os.makedirs(os.path.dirname(staged_path), exist_ok=True)
        with open(staged_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.generated_files.append(safe_rel)
        return True, "staged"

    def commit(self) -> list[str]:
        if not self._active or not self.staging_dir:
            return []
        committed = []
        for rel_path in self.generated_files:
            src = os.path.join(self.staging_dir, rel_path)
            dst = os.path.join(self.project_root, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
            committed.append(rel_path)
        self._cleanup()
        return committed

    def rollback(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        if self.staging_dir and os.path.exists(self.staging_dir):
            shutil.rmtree(self.staging_dir, ignore_errors=True)
        self.staging_dir = None
        self._active = False
