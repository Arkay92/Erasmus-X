import time

class FailureLearner:
    def __init__(self, brain=None):
        self.brain = brain

    def record_failure(self, stack, request, failures, critic_report):
        """Records a build failure into the brain's deterministic failure log."""
        if not self.brain:
            print("[!] FailureLearner: No brain provided, cannot record failure.")
            return

        record = {
            "timestamp": time.time(),
            "stack": stack,
            "request": request,
            "failures": failures,
            "critic_report": critic_report
        }
        
        self.brain.record_failure(record)
        print(f"[*] Failure Learned and embedded into Neurosymbolic Brain.")

    def get_recent_failures(self, limit=3):
        """Retrieves recent failures from the brain's deterministic log."""
        if not self.brain: return []
        return self.brain.get_recent_failures(limit)
