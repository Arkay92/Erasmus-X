import concurrent.futures
import time
import uuid
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Any, Callable, Optional


@dataclass(order=True)
class QueuedTask:
    priority: int
    created_at: float
    job_id: str = field(compare=False)
    payload: Any = field(compare=False)


class TaskQueue:
    """In-process priority queue with worker-pool execution.

    This is API-compatible with a future Redis/RabbitMQ backend while keeping
    local tests and development dependency-free.
    """

    def __init__(self, handler: Optional[Callable[[Any], Any]] = None, num_workers: int = 4):
        self.handler = handler
        self.queue: PriorityQueue[QueuedTask] = PriorityQueue()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.status: dict[str, dict[str, Any]] = {}

    def enqueue(self, task: Any, priority: int = 5) -> str:
        job_id = uuid.uuid4().hex
        self.status[job_id] = {"state": "queued", "result": None, "error": None}
        self.queue.put(QueuedTask(priority, time.time(), job_id, task))
        return job_id

    def process_next(self) -> Optional[str]:
        if self.queue.empty():
            return None
        queued = self.queue.get()
        self.status[queued.job_id]["state"] = "running"
        future = self.executor.submit(self._run, queued.job_id, queued.payload)
        self.status[queued.job_id]["future"] = future
        return queued.job_id

    def drain(self) -> list[str]:
        jobs = []
        while not self.queue.empty():
            job_id = self.process_next()
            if job_id:
                jobs.append(job_id)
        return jobs

    def get_status(self, job_id: str) -> dict[str, Any]:
        record = self.status.get(job_id)
        if not record:
            return {"state": "missing", "result": None, "error": "unknown job"}
        future = record.get("future")
        if future and future.done() and record["state"] == "running":
            try:
                record["result"] = future.result()
                record["state"] = "completed"
            except Exception as exc:
                record["error"] = str(exc)
                record["state"] = "failed"
        return {k: v for k, v in record.items() if k != "future"}

    def _run(self, job_id: str, payload: Any) -> Any:
        if not self.handler:
            return payload
        return self.handler(payload)
