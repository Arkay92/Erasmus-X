import time
from core import config, prompts

class SessionManager:
    def __init__(self, brain, client):
        self.brain = brain
        self.client = client

    def get_structured_state(self):
        """Retrieves formatted session recap from the brain."""
        latest_state = self.brain.get_latest_session_state()
        if latest_state:
            return f"[SESSION_STATE] Summary: {latest_state}"
        return None

    def perform_spin_down(self, history, current_task=""):
        """Summarizes and persists session state."""
        if not history:
            return False
            
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
        latest_state = self.get_structured_state() or "None"
        
        summary_prompt = prompts.GROUNDED_SUMMARY_PROMPT.format(
            retrieved_context=latest_state,
            history_context=history_text
        )
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1,
                max_tokens=400
            )
            summary = response.choices[0].message.content
            
            # Save to brain with structured marker
            self.brain.add_document(f"[SESSION_STATE] Summary: {summary}")
            return True
        except Exception:
            return False

    def check_stability_trigger(self, history):
        """Checks if history is nearing token limits."""
        # Simple character-based heuristic or token count
        from utils.text_utils import count_tokens
        history_tokens = sum(count_tokens(m['content']) for m in history)
        return history_tokens > config.FAST_MODE_CONTEXT_TOKENS * 0.8
