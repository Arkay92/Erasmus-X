import os
import tempfile
import uuid


def ensure_writable_dir(path: str, fallback_name: str) -> str:
    """Return a writable directory, falling back to temp if the preferred path is blocked."""
    preferred = os.path.abspath(path)
    try:
        os.makedirs(preferred, exist_ok=True)
        probe = os.path.join(preferred, f".write_probe_{uuid.uuid4().hex}")
        with open(probe, "x", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return preferred
    except Exception as exc:
        fallback = os.path.join(tempfile.gettempdir(), "erasmus_cell_runtime", fallback_name)
        os.makedirs(fallback, exist_ok=True)
        print(f"[!] Runtime path fallback: {preferred} is not writable ({exc}). Using {fallback}")
        return fallback


def ensure_writable_file_path(path: str, fallback_name: str) -> str:
    directory = ensure_writable_dir(os.path.dirname(path), fallback_name)
    return os.path.join(directory, os.path.basename(path))
