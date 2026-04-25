import re
from core import config

class TaskRouter:
    def __init__(self, brain, local_llm):
        self.brain = brain
        self.local_llm = local_llm

    def route(self, user_input):
        """Classifies intent and determines operating mode."""
        intent, confidence = self.brain.classify_intent(user_input)
        
        # 1. Complexity Check (Gating)
        mode = config.OPERATING_MODE
        if self._is_complex_reasoning(user_input, intent, confidence):
            mode = "DEEP"
            
        return {
            'intent': intent,
            'confidence': confidence,
            'mode': mode,
            'is_code': any(k in user_input.lower() for k in ['write', 'code', 'script', 'implement', 'algorithm', 'project'])
        }

    def _is_complex_reasoning(self, text, intent, confidence):
        """Heuristic for complexity escalation."""
        if any(k in text.lower() for k in ['complex', 'architecture', 'system', 'refactor', 'debug', 'project']):
            return True
        if intent == "PROJECT" and confidence > 0.3:
            return True
        if len(text.split()) > config.SIMPLE_QUERY_LIMIT:
            return True
        return False

class ExecutionController:
    def __init__(self, client):
        self.client = client

    def enforce_contract(self, user_input, response_text, task_metadata):
        """Ensures the response matches the task type requirements."""
        if task_metadata['is_code'] and "[FILE:" not in response_text:
            return False, "Code task detected but no [FILE:] tags found. You must implement the source code."
        
        if task_metadata['intent'] == "PROJECT" and "PLAN.md" not in response_text and "[FILE:" not in response_text:
             return False, "Project request detected. You must provide a plan or implement files."
             
        return True, "Contract satisfied"
