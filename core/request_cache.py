import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any, Optional

from core import config


class RequestCache:
    """Small deterministic request cache with optional disk persistence.

    The cache is intentionally dependency-free. If Redis is added later, this
    class is the single integration point for a distributed cache backend.
    """

    def __init__(self, max_bytes: Optional[int] = None, storage_path: Optional[str] = None):
        self.max_bytes = max_bytes or getattr(config, "REQUEST_CACHE_MAX_BYTES", 100_000_000)
        self.storage_path = storage_path or config.REQUEST_CACHE_PATH
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._bytes = 0
        self._load()

    def fingerprint(self, request: Any, **metadata: Any) -> str:
        payload = {
            "request": request,
            "metadata": metadata,
            "cache_version": getattr(config, "REQUEST_CACHE_VERSION", "v1"),
        }
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, fingerprint: str) -> Optional[Any]:
        item = self._items.get(fingerprint)
        if not item:
            return None
        expires_at = item.get("expires_at")
        if expires_at and expires_at < time.time():
            self._drop(fingerprint)
            self._safe_save()
            return None
        self._items.move_to_end(fingerprint)
        return item.get("value")

    def set(self, fingerprint: str, value: Any, ttl: int = 24 * 3600) -> None:
        encoded = json.dumps(value, sort_keys=True, default=str)
        item = {
            "value": value,
            "size": len(encoded.encode("utf-8")),
            "created_at": time.time(),
            "expires_at": time.time() + ttl if ttl else None,
        }
        if fingerprint in self._items:
            self._drop(fingerprint)
        self._items[fingerprint] = item
        self._bytes += item["size"]
        self._evict()
        self._safe_save()

    def _drop(self, key: str) -> None:
        item = self._items.pop(key, None)
        if item:
            self._bytes -= item.get("size", 0)

    def _evict(self) -> None:
        while self._bytes > self.max_bytes and self._items:
            key, _ = next(iter(self._items.items()))
            self._drop(key)

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            now = time.time()
            for key, item in raw.get("items", {}).items():
                if item.get("expires_at") and item["expires_at"] < now:
                    continue
                self._items[key] = item
                self._bytes += item.get("size", 0)
            self._evict()
        except Exception:
            self._items.clear()
            self._bytes = 0

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        data = {"items": self._items}
        tmp_path = self.storage_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp_path, self.storage_path)

    def _safe_save(self) -> None:
        try:
            self._save()
        except OSError as exc:
            print(f"[!] Request cache persistence skipped: {exc}")
