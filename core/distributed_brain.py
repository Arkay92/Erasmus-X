from typing import Any


class DistributedBrain:
    """Replicates documents to local brain and an optional secondary index."""

    def __init__(self, local_brain: Any, remote_index: Any | None = None):
        self.local_brain = local_brain
        self.remote_index = remote_index

    def add_document(self, doc: str) -> None:
        self.local_brain.add_document(doc)
        if self.remote_index and hasattr(self.remote_index, "add_document"):
            self.remote_index.add_document(doc)

    def search(self, query: str, threshold: float = 0.15, top_k: int = 3):
        local_results = self.local_brain.search(query, threshold=threshold, top_k=top_k)
        if local_results:
            return local_results
        if self.remote_index and hasattr(self.remote_index, "search"):
            return self.remote_index.search(query, threshold=threshold, top_k=top_k)
        return []

    def sync(self) -> bool:
        if self.remote_index and hasattr(self.remote_index, "sync"):
            return bool(self.remote_index.sync())
        return True
