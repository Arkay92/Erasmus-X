import uuid
from core import config

class Subagent:
    """A scoped, task-specific agent spawned by the Orchestrator."""
    def __init__(self, agent_id, role, parent_agent):
        self.agent_id = agent_id
        self.role = role
        self.parent = parent_agent
        self.memory = []
        self.results = None

    def execute(self, task_description):
        print(f"[Subagent {self.agent_id} ({self.role})] Executing: {task_description[:50]}...")
        # Use the parent's infrastructure but with a scoped prompt
        scoped_user_input = f"ROLE: {self.role}\nTASK: {task_description}\n\nStrictly follow role-based constraints."
        
        # Subagents always run in FAST mode unless the task is huge
        raw_resp, clean_resp = self.parent.chat(scoped_user_input, mode_override="FAST")
        self.results = clean_resp
        return self.results

class SubagentManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.active_subagents = {}

    def spawn(self, role):
        agent_id = str(uuid.uuid4())[:8]
        subagent = Subagent(agent_id, role, self.orchestrator)
        self.active_subagents[agent_id] = subagent
        print(f"[+] Spawned Subagent {agent_id} for role: {role}")
        return subagent

    def delegate_and_collect(self, delegations):
        """
        delegations: List of (role, task) tuples
        """
        results = {}
        for role, task in delegations:
            sub = self.spawn(role)
            res = sub.execute(task)
            results[role] = res
        return results
