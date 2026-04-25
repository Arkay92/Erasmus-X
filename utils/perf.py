import time
from contextlib import contextmanager

class LatencyTracker:
    def __init__(self):
        self.stages = {}

    @contextmanager
    def track(self, stage_name):
        start = time.perf_counter()
        yield
        duration = time.perf_counter() - start
        self.stages[stage_name] = duration
        print(f"[LATENCY] {stage_name}: {duration:.4f}s")

    def get_report(self):
        return self.stages

# Global instance for easy access
tracker = LatencyTracker()
